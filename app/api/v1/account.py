from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

from app.accounting.models import BankAccount, CreditCardAccount, Deposit, JournalEntry, JournalLine, Loan
from app.core.models import Entity, User
from app.database.engine import get_db
from app.document_imports.models import ImportBatch, ImportedOperation
from app.investing.models import Broker, Portfolio, PortfolioValuationSnapshot, Position, Trade
from app.core.settings import settings
from app.security.local_lock import (
    generate_recovery_code, hash_secret, issue_session, normalize_recovery_code,
    needs_rehash, revoke_session, revoke_user_sessions, validate_new_password, verify_secret,
)
from app.security.web_auth import SESSION_COOKIE, get_session

router = APIRouter(prefix="/account", tags=["Account"])


class QuickActionPreferences(BaseModel):
    quick_action_ids: list[str] = Field(min_length=9, max_length=9)


class LanguagePreference(BaseModel):
    preferred_language: str = Field(pattern="^(ar|en)$")


class AccountProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    nationality: str | None = Field(default=None, max_length=80)
    country_of_residence: str | None = Field(default=None, max_length=80)
    tax_residence: str | None = Field(default=None, max_length=80)
    investor_type: str = Field(default="INDIVIDUAL", pattern="^(INDIVIDUAL|ENTITY)$")
    default_dividend_withholding_tax_rate: Decimal = Field(default=0, ge=0, le=100)

    @field_validator("full_name", "email", "nationality", "country_of_residence", "tax_residence")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SetupCompleteRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    local_password: str | None = Field(default=None, min_length=12, max_length=256)
    preferred_language: str = Field(pattern="^(ar|en)$")
    base_currency_code: str = Field(pattern="^[A-Z]{3}$")
    enabled_currency_codes: list[str] = Field(min_length=1, max_length=8)
    nationality: str | None = Field(default=None, max_length=80)
    country_of_residence: str | None = Field(default=None, max_length=80)
    tax_residence: str | None = Field(default=None, max_length=80)
    investor_type: str = Field(default="INDIVIDUAL", pattern="^(INDIVIDUAL|ENTITY)$")
    local_data_acknowledged: bool
    existing_data_choice: str | None = Field(default=None, pattern="^(RESUME_EXISTING|START_CLEAN|REVIEW_MIGRATION)$")


def _has_existing_financial_data(db: Session, user: User) -> bool:
    return any(
        query.first() is not None
        for query in (
            db.query(JournalEntry.id).filter(JournalEntry.user_id == user.id),
            db.query(BankAccount.id).filter(BankAccount.user_id == user.id),
            db.query(CreditCardAccount.id).filter(CreditCardAccount.user_id == user.id),
            db.query(Deposit.id).filter(Deposit.user_id == user.id),
            db.query(Loan.id).filter(Loan.user_id == user.id),
            db.query(ImportBatch.id).filter(ImportBatch.user_id == user.id),
        )
    )


_password_hash = hash_secret
_password_matches = verify_secret


class UnlockRequest(BaseModel):
    local_password: str = Field(min_length=1, max_length=256)


class RecoveryRequest(BaseModel):
    recovery_code: str = Field(min_length=32, max_length=80)
    new_local_password: str = Field(min_length=12, max_length=256)


class PasswordChangeRequest(BaseModel):
    current_local_password: str = Field(min_length=1, max_length=256)
    new_local_password: str = Field(min_length=12, max_length=256)


class PasswordDisableRequest(BaseModel):
    current_local_password: str = Field(min_length=1, max_length=256)


def _sessions(request: Request):
    if not hasattr(request.app.state, "unlock_sessions"):
        request.app.state.unlock_sessions = {}
    return request.app.state.unlock_sessions


def _set_desktop_window_mode(request: Request, mode: str) -> None:
    callback = getattr(request.app.state, "desktop_window_mode_callback", None)
    if callback is not None:
        callback(mode)


def _session_binding(request: Request) -> tuple[str, str]:
    return (
        str(getattr(request.app.state, "installation_id", "test-installation")),
        str(getattr(request.app.state, "local_principal_sid", "test-principal")),
    )


def _issue_unlock_cookie(request: Request, user: User):
    installation_id, principal_sid = _session_binding(request)
    return issue_session(_sessions(request), user_id=user.id, installation_id=installation_id,
                         principal_sid=principal_sid, security_version=user.security_state_version)


def _set_unlock_cookie(response: dict, token: str):
    from fastapi.responses import JSONResponse
    result = JSONResponse(response)
    result.set_cookie("wealthos_unlock", token, httponly=True, samesite="strict", path="/")
    return result


def _allowed_after(value: datetime | None, now: datetime) -> bool:
    if value and value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return not value or now >= value


def _failure_delay(attempts: int) -> int:
    return min(900, 2 ** (attempts - 5) * 2) if attempts >= 5 else 0


def local_user(db: Session = Depends(get_db)) -> User:
    # Local beta identity is selected by trusted server configuration, never by a client header.
    user = db.query(User).filter(User.id == settings.LOCAL_USER_ID, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Account is not available.")
    return user


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    # Preserve the callable contract used by local-mode service tests while the
    # FastAPI dependency path always supplies a Request and database session.
    if isinstance(request, User):
        if not request.setup_completed:
            raise HTTPException(status_code=423, detail="Local setup is required.")
        return request
    if settings.WEB_MODE:
        session = get_session(db, request.cookies.get(SESSION_COOKIE, ""))
        if session is None:
            raise HTTPException(status_code=401, detail={"key": "auth.required"})
        user = db.query(User).filter(User.id == session.user_id, User.is_active.is_(True)).first()
        if user is None or user.security_state_version != session.security_version:
            raise HTTPException(status_code=401, detail={"key": "auth.session_invalid"})
        return user
    user = local_user(db)
    if not user.setup_completed:
        raise HTTPException(status_code=423, detail="Local setup is required.")
    return user


def rows(query):
    return [{column.name: getattr(item, column.name) for column in item.__table__.columns} for item in query.all()]


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "username": user.username, "email": user.email, "full_name": user.full_name, "created_at": user.created_at, "preferred_language": user.preferred_language, "locale": user.locale, "nationality": user.nationality, "country_of_residence": user.country_of_residence, "tax_residence": user.tax_residence, "investor_type": user.investor_type, "default_dividend_withholding_tax_rate": user.default_dividend_withholding_tax_rate}


@router.get("/setup-status")
def setup_status(request: Request, user: User = Depends(local_user), db: Session = Depends(get_db)):
    request.app.state.setup_incomplete = not bool(user.setup_completed)
    requires_unlock = bool(user.setup_completed and user.password_hash)
    unlocked = not requires_unlock or bool(getattr(request.state, "account_unlocked", False))
    _set_desktop_window_mode(request, "main" if user.setup_completed and unlocked else "compact")
    if requires_unlock and not unlocked:
        return {"completed": True, "has_existing_data": False, "legacy_data_found": False,
                "requires_unlock": True, "unlocked": False, "profile": None}
    return {
        "completed": user.setup_completed,
        "has_existing_data": _has_existing_financial_data(db, user),
        "legacy_data_found": bool(getattr(request.app.state, "legacy_candidate_count", 0)),
        "requires_unlock": requires_unlock,
        "unlocked": unlocked,
        "profile": None if not unlocked else {"id": user.id, "full_name": user.full_name, "email": user.email},
    }


@router.post("/setup")
def complete_setup(payload: SetupCompleteRequest, request: Request, user: User = Depends(local_user), db: Session = Depends(get_db)):
    if user.setup_completed:
        raise HTTPException(status_code=409, detail="Local setup is already complete.")
    if not payload.local_data_acknowledged:
        raise HTTPException(status_code=400, detail="Local data storage acknowledgement is required.")
    has_existing_data = _has_existing_financial_data(db, user)
    legacy_data_found = bool(getattr(request.app.state, "legacy_candidate_count", 0))
    if has_existing_data and payload.existing_data_choice != "RESUME_EXISTING":
        raise HTTPException(status_code=409, detail="Existing financial data requires an explicit resume choice or migration review.")
    if payload.existing_data_choice == "REVIEW_MIGRATION":
        raise HTTPException(status_code=409, detail="Migration review requested; no data was activated or changed.")
    if legacy_data_found and not has_existing_data and payload.existing_data_choice != "START_CLEAN":
        raise HTTPException(status_code=409, detail="Prior beta data remains untouched; choose a clean workspace or migration review.")
    enabled = list(dict.fromkeys(code.upper() for code in payload.enabled_currency_codes))
    if payload.base_currency_code not in enabled or any(len(code) != 3 or not code.isalpha() for code in enabled):
        raise HTTPException(status_code=400, detail="Enabled currencies must include the base currency.")
    user.full_name = payload.full_name.strip()
    user.email = payload.email.strip().lower()
    recovery_code = None
    if payload.local_password:
        try:
            validate_new_password(payload.local_password)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        recovery_code = generate_recovery_code()
        user.password_hash = hash_secret(payload.local_password)
        user.recovery_code_hash = hash_secret(normalize_recovery_code(recovery_code))
        user.security_state_version += 1
    else:
        user.password_hash = None
        user.recovery_code_hash = None
    user.preferred_language = payload.preferred_language
    user.base_currency_code = payload.base_currency_code
    user.enabled_currency_codes = enabled
    user.nationality = payload.nationality.strip() if payload.nationality else None
    user.country_of_residence = payload.country_of_residence.strip() if payload.country_of_residence else None
    user.tax_residence = payload.tax_residence.strip() if payload.tax_residence else None
    user.investor_type = payload.investor_type
    user.local_data_acknowledged = True
    user.setup_migration_choice = payload.existing_data_choice
    user.setup_completed = True
    db.commit()
    request.app.state.setup_incomplete = False
    db.info["setup_password_created"] = bool(payload.local_password)
    result = {"completed": True, "profile": {"id": user.id, "full_name": user.full_name, "email": user.email},
              "recovery_code": recovery_code}
    if payload.local_password:
        return _set_unlock_cookie(result, _issue_unlock_cookie(request, user))
    return result


@router.get("/unlock-status")
def unlock_status():
    return {"requires_unlock": True}


@router.post("/unlock")
def unlock(payload: UnlockRequest, request: Request, user: User = Depends(local_user), db: Session = Depends(get_db)):
    now = datetime.now(UTC)
    allowed = _allowed_after(user.next_unlock_allowed_at, now)
    valid = allowed and user.setup_completed and bool(user.password_hash) and verify_secret(payload.local_password, user.password_hash)
    if not valid:
        if allowed:
            user.failed_unlock_attempts += 1
            if user.failed_unlock_attempts >= 5:
                delay = min(900, 2 ** (user.failed_unlock_attempts - 5) * 2)
                user.next_unlock_allowed_at = now + timedelta(seconds=delay)
            db.commit()
        raise HTTPException(status_code=401, detail="The local password is incorrect.")
    user.failed_unlock_attempts = 0
    user.next_unlock_allowed_at = None
    if needs_rehash(user.password_hash):
        user.password_hash = hash_secret(payload.local_password)
    db.commit()
    return _set_unlock_cookie({"unlocked": True}, _issue_unlock_cookie(request, user))


@router.post("/lock")
def lock(request: Request):
    from fastapi.responses import JSONResponse
    revoke_session(_sessions(request), request.cookies.get("wealthos_unlock", ""))
    result = JSONResponse({"locked": True})
    result.delete_cookie("wealthos_unlock", path="/")
    _set_desktop_window_mode(request, "compact")
    return result


@router.post("/recover")
def recover(payload: RecoveryRequest, request: Request, user: User = Depends(local_user), db: Session = Depends(get_db)):
    try:
        validate_new_password(payload.new_local_password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    now = datetime.now(UTC)
    allowed = _allowed_after(user.next_recovery_allowed_at, now)
    valid = allowed and user.setup_completed and verify_secret(normalize_recovery_code(payload.recovery_code), user.recovery_code_hash)
    if not valid:
        if allowed:
            user.failed_recovery_attempts += 1
            delay = _failure_delay(user.failed_recovery_attempts)
            if delay:
                user.next_recovery_allowed_at = now + timedelta(seconds=delay)
            db.commit()
        raise HTTPException(status_code=401, detail="Recovery could not be completed.")
    recovery_code = generate_recovery_code()
    user.password_hash = hash_secret(payload.new_local_password)
    user.recovery_code_hash = hash_secret(normalize_recovery_code(recovery_code))
    user.security_state_version += 1
    user.failed_unlock_attempts = 0
    user.next_unlock_allowed_at = None
    user.failed_recovery_attempts = 0
    user.next_recovery_allowed_at = None
    db.commit()
    revoke_user_sessions(_sessions(request), user.id)
    return _set_unlock_cookie({"recovered": True, "recovery_code": recovery_code}, _issue_unlock_cookie(request, user))


def _require_recent_password(user: User, password: str, db: Session) -> None:
    # The credential is checked within this request, which is stricter than the
    # permitted five-minute re-verification window.
    now = datetime.now(UTC)
    allowed = _allowed_after(user.next_unlock_allowed_at, now)
    if not allowed or not verify_secret(password, user.password_hash):
        if allowed:
            user.failed_unlock_attempts += 1
            delay = _failure_delay(user.failed_unlock_attempts)
            if delay:
                user.next_unlock_allowed_at = now + timedelta(seconds=delay)
            db.commit()
        raise HTTPException(status_code=401, detail="Password verification is required.")
    user.failed_unlock_attempts = 0
    user.next_unlock_allowed_at = None


@router.post("/password/change")
def change_password(payload: PasswordChangeRequest, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_recent_password(user, payload.current_local_password, db)
    try:
        validate_new_password(payload.new_local_password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    recovery_code = generate_recovery_code()
    user.password_hash = hash_secret(payload.new_local_password)
    user.recovery_code_hash = hash_secret(normalize_recovery_code(recovery_code))
    user.security_state_version += 1
    db.commit()
    revoke_user_sessions(_sessions(request), user.id)
    return _set_unlock_cookie({"changed": True, "recovery_code": recovery_code}, _issue_unlock_cookie(request, user))


@router.post("/password/disable")
def disable_password(payload: PasswordDisableRequest, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_recent_password(user, payload.current_local_password, db)
    user.password_hash = None
    user.recovery_code_hash = None
    user.security_state_version += 1
    db.commit()
    revoke_user_sessions(_sessions(request), user.id)
    from fastapi.responses import JSONResponse
    result = JSONResponse({"disabled": True})
    result.delete_cookie("wealthos_unlock", path="/")
    return result


@router.patch("/me")
def update_me(request: AccountProfileUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    duplicate = db.query(User).filter(User.email.ilike(request.email), User.id != user.id).first()
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="This email address is already in use.")
    user.full_name = request.full_name
    user.email = request.email.lower()
    user.nationality = request.nationality
    user.country_of_residence = request.country_of_residence
    user.tax_residence = request.tax_residence
    user.investor_type = request.investor_type
    user.default_dividend_withholding_tax_rate = request.default_dividend_withholding_tax_rate
    db.commit()
    db.refresh(user)
    return me(user)


@router.get("/preferences")
def preferences(user: User = Depends(current_user)):
    return {"quick_action_ids": user.quick_action_ids}


@router.patch("/preferences")
def update_preferences(request: QuickActionPreferences, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.quick_action_ids = list(dict.fromkeys(request.quick_action_ids))
    db.commit()
    db.refresh(user)
    return {"quick_action_ids": user.quick_action_ids}


@router.patch("/preferences/language")
def update_language_preference(request: LanguagePreference, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.preferred_language = request.preferred_language
    db.commit()
    db.refresh(user)
    return {"preferred_language": user.preferred_language}


@router.get("/backup")
def backup(user: User = Depends(current_user), db: Session = Depends(get_db)):
    entity_ids = [item.id for item in db.query(Entity.id).filter(Entity.user_id == user.id)]
    portfolio_ids = [item.id for item in db.query(Portfolio.id).filter(Portfolio.entity_id.in_(entity_ids))] if entity_ids else []
    entry_ids = [item.id for item in db.query(JournalEntry.id).filter(JournalEntry.user_id == user.id)]
    batch_ids = [item.id for item in db.query(ImportBatch.id).filter(ImportBatch.user_id == user.id)]
    return {
        "format": "WealthOS Account Backup", "version": 1, "exported_at": datetime.now(UTC),
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "created_at": user.created_at},
        "data": {
            "entities": rows(db.query(Entity).filter(Entity.user_id == user.id)),
            "portfolios": rows(db.query(Portfolio).filter(Portfolio.entity_id.in_(entity_ids))) if entity_ids else [],
            "positions": rows(db.query(Position).filter(Position.portfolio_id.in_(portfolio_ids))) if portfolio_ids else [],
            "trades": rows(db.query(Trade).filter(Trade.portfolio_id.in_(portfolio_ids))) if portfolio_ids else [],
            "brokers": rows(db.query(Broker).filter(Broker.user_id == user.id)),
            "journal_entries": rows(db.query(JournalEntry).filter(JournalEntry.user_id == user.id)),
            "journal_lines": rows(db.query(JournalLine).filter(JournalLine.journal_entry_id.in_(entry_ids))) if entry_ids else [],
            "loans": rows(db.query(Loan).filter(Loan.user_id == user.id)),
            "bank_accounts": rows(db.query(BankAccount).filter(BankAccount.user_id == user.id)),
            "credit_card_accounts": rows(db.query(CreditCardAccount).filter(CreditCardAccount.user_id == user.id)),
            "deposits": rows(db.query(Deposit).filter(Deposit.user_id == user.id)),
            "portfolio_valuation_snapshots": rows(db.query(PortfolioValuationSnapshot).filter(PortfolioValuationSnapshot.user_id == user.id)),
            "import_batches": rows(db.query(ImportBatch).filter(ImportBatch.user_id == user.id)),
            "imported_operations": rows(db.query(ImportedOperation).filter(ImportedOperation.batch_id.in_(batch_ids))) if batch_ids else [],
        },
    }


@router.delete("")
def delete_account(confirm_email: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if confirm_email.strip().lower() != user.email.lower():
        raise HTTPException(status_code=400, detail="Email confirmation does not match.")
    entity_ids = [item.id for item in db.query(Entity.id).filter(Entity.user_id == user.id)]
    portfolio_ids = [item.id for item in db.query(Portfolio.id).filter(Portfolio.entity_id.in_(entity_ids))] if entity_ids else []
    entry_ids = [item.id for item in db.query(JournalEntry.id).filter(JournalEntry.user_id == user.id)]
    batch_ids = [item.id for item in db.query(ImportBatch.id).filter(ImportBatch.user_id == user.id)]
    if portfolio_ids:
        db.query(Trade).filter(Trade.portfolio_id.in_(portfolio_ids)).delete(synchronize_session=False)
        db.query(Position).filter(Position.portfolio_id.in_(portfolio_ids)).delete(synchronize_session=False)
        db.query(Portfolio).filter(Portfolio.id.in_(portfolio_ids)).delete(synchronize_session=False)
    if batch_ids:
        db.query(ImportedOperation).filter(ImportedOperation.batch_id.in_(batch_ids)).delete(synchronize_session=False)
    db.query(ImportBatch).filter(ImportBatch.user_id == user.id).delete(synchronize_session=False)
    db.query(Loan).filter(Loan.user_id == user.id).delete(synchronize_session=False)
    db.query(Deposit).filter(Deposit.user_id == user.id).delete(synchronize_session=False)
    db.query(BankAccount).filter(BankAccount.user_id == user.id).delete(synchronize_session=False)
    db.query(CreditCardAccount).filter(CreditCardAccount.user_id == user.id).delete(synchronize_session=False)
    db.query(PortfolioValuationSnapshot).filter(PortfolioValuationSnapshot.user_id == user.id).delete(synchronize_session=False)
    if entry_ids:
        db.query(JournalLine).filter(JournalLine.journal_entry_id.in_(entry_ids)).delete(synchronize_session=False)
    db.query(JournalEntry).filter(JournalEntry.user_id == user.id).delete(synchronize_session=False)
    db.query(Broker).filter(Broker.user_id == user.id).delete(synchronize_session=False)
    db.query(Entity).filter(Entity.user_id == user.id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
    return {"deleted": True}
