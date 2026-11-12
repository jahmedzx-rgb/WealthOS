import hashlib
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.models.user import User
from app.core.settings import settings
from app.database.engine import get_db
from app.security.local_lock import (
    generate_recovery_code,
    hash_secret,
    needs_rehash,
    normalize_recovery_code,
    validate_new_password,
    verify_secret,
)
from app.security.models import WebInviteCode, WebRegistrationSlot
from app.security.web_auth import CSRF_COOKIE, SESSION_COOKIE, check_rate_limit, client_key, get_session, issue_session, normalize_username, revoke_session, revoke_user_sessions

router = APIRouter(prefix="/auth", tags=["Authentication"])


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=12, max_length=256)
    locale: str = Field(default="en", pattern="^(ar|en)$")
    invite_code: str = Field(min_length=16, max_length=128)

    @field_validator("username")
    @classmethod
    def clean_username(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or any(character.isspace() for character in cleaned):
            raise ValueError("auth.username_invalid")
        return cleaned


class LoginCredentials(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=12, max_length=256)


class RecoveryCredentials(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    recovery_code: str = Field(min_length=32, max_length=80)
    new_password: str = Field(min_length=12, max_length=256)


DUMMY_PASSWORD_HASH = hash_secret("wealthos-constant-time-dummy-password")


def _require_web() -> None:
    if not settings.WEB_MODE:
        raise HTTPException(status_code=404, detail={"key": "auth.web_only"})


def _set_auth_cookies(response: Response, token: str, csrf: str) -> None:
    common = {"secure": settings.COOKIE_SECURE, "samesite": "strict", "path": "/", "max_age": settings.WEB_SESSION_HOURS * 3600}
    response.set_cookie(SESSION_COOKIE, token, httponly=True, **common)
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, **common)


@router.post("/register", status_code=201)
def register(payload: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    _require_web()
    check_rate_limit(db, client_key(request, "register"), 20, 3600)
    try:
        validate_new_password(payload.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"key": "auth.password_weak"}) from error
    normalized = normalize_username(payload.username)
    if len(normalized) < 3:
        raise HTTPException(status_code=400, detail={"key": "auth.username_invalid"})
    try:
        invite_hash = hashlib.sha256(payload.invite_code.strip().encode("utf-8")).hexdigest()
        invite = db.query(WebInviteCode).filter(WebInviteCode.code_hash == invite_hash, WebInviteCode.used_by_user_id.is_(None)).with_for_update().first()
        if invite is None:
            db.rollback()
            raise HTTPException(status_code=403, detail={"key": "auth.invite_invalid"})
        if invite.is_admin and db.query(User).filter(User.is_admin.is_(True)).first() is not None:
            db.rollback()
            raise HTTPException(status_code=403, detail={"key": "auth.invite_invalid"})
        user = None
        if invite.is_admin:
            # A restored local database owns its financial rows through the
            # legacy placeholder user. Claim that row for the first admin so
            # the imported data remains visible in the web account.
            user = db.query(User).filter(
                User.id == settings.LOCAL_USER_ID,
                User.username.is_(None),
            ).with_for_update().first()
        if user is None:
            user = User(
                email=f"{secrets.token_hex(12)}@account.wealthos.invalid",
                full_name=payload.username,
                password_hash=hash_secret(payload.password),
                preferred_language=payload.locale,
                locale=payload.locale,
            )
            db.add(user)
        user.username = payload.username
        user.username_normalized = normalized
        if user.id != settings.LOCAL_USER_ID or not user.full_name:
            user.full_name = payload.username
        recovery_code = generate_recovery_code()
        user.password_hash = hash_secret(payload.password)
        user.recovery_code_hash = hash_secret(normalize_recovery_code(recovery_code))
        user.setup_completed = True
        user.local_data_acknowledged = True
        user.is_active = True
        user.is_admin = invite.is_admin
        db.flush()
        invite.used_by_user_id = user.id
        invite.used_at = datetime.now(UTC)
        reserved = False
        for slot in range(1, settings.WEB_MAX_USERS + 1):
            try:
                with db.begin_nested():
                    db.add(WebRegistrationSlot(slot=slot, user_id=user.id))
                    db.flush()
                reserved = True
                break
            except IntegrityError:
                continue
        if not reserved:
            db.rollback()
            raise HTTPException(status_code=403, detail={"key": "auth.registration_full"})
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail={"key": "auth.username_taken"}) from error
    db.refresh(user)
    token, csrf = issue_session(db, user.id, user.security_state_version)
    _set_auth_cookies(response, token, csrf)
    return {"id": user.id, "username": user.username, "locale": user.locale, "is_admin": user.is_admin,
            "recovery_code": recovery_code}


@router.post("/login")
def login(payload: LoginCredentials, request: Request, response: Response, db: Session = Depends(get_db)):
    _require_web()
    normalized = normalize_username(payload.username)
    check_rate_limit(db, client_key(request, f"login:{normalized}"), 10, 300)
    user = db.query(User).filter(User.username_normalized == normalized, User.is_active.is_(True)).first()
    valid = verify_secret(payload.password, user.password_hash if user is not None else DUMMY_PASSWORD_HASH)
    if user is None or not valid:
        raise HTTPException(status_code=401, detail={"key": "auth.invalid_credentials"})
    if needs_rehash(user.password_hash):
        user.password_hash = hash_secret(payload.password)
    db.commit()
    token, csrf = issue_session(db, user.id, user.security_state_version)
    _set_auth_cookies(response, token, csrf)
    return {"id": user.id, "username": user.username, "locale": user.locale, "is_admin": user.is_admin}


@router.post("/recover")
def recover(payload: RecoveryCredentials, request: Request, response: Response, db: Session = Depends(get_db)):
    _require_web()
    normalized = normalize_username(payload.username)
    check_rate_limit(db, client_key(request, f"recover:{normalized}"), 8, 900)
    user = db.query(User).filter(User.username_normalized == normalized, User.is_active.is_(True)).first()
    supplied_code = normalize_recovery_code(payload.recovery_code)
    valid = verify_secret(
        supplied_code,
        user.recovery_code_hash if user is not None and user.recovery_code_hash else DUMMY_PASSWORD_HASH,
    )
    if user is None or not valid:
        raise HTTPException(status_code=401, detail={"key": "auth.recovery_invalid"})
    try:
        validate_new_password(payload.new_password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"key": "auth.password_weak"}) from error
    replacement_code = generate_recovery_code()
    user.password_hash = hash_secret(payload.new_password)
    user.recovery_code_hash = hash_secret(normalize_recovery_code(replacement_code))
    user.security_state_version += 1
    db.commit()
    revoke_user_sessions(db, user.id)
    token, csrf = issue_session(db, user.id, user.security_state_version)
    _set_auth_cookies(response, token, csrf)
    return {"recovered": True, "recovery_code": replacement_code}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    _require_web()
    revoke_session(db, request.cookies.get(SESSION_COOKIE, ""))
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"logged_out": True}


@router.post("/logout-all")
def logout_all(request: Request, response: Response, db: Session = Depends(get_db)):
    _require_web()
    session = get_session(db, request.cookies.get(SESSION_COOKIE, ""))
    if session is None:
        raise HTTPException(status_code=401, detail={"key": "auth.required"})
    revoke_user_sessions(db, session.user_id)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"logged_out_all": True}
