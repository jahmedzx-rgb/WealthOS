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
from app.security.local_lock import hash_secret, needs_rehash, validate_new_password, verify_secret
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
    user = User(username=payload.username, username_normalized=normalized,
                email=f"{secrets.token_hex(12)}@account.wealthos.invalid", full_name=payload.username,
                password_hash=hash_secret(payload.password), preferred_language=payload.locale, locale=payload.locale,
                setup_completed=True, local_data_acknowledged=True)
    db.add(user)
    try:
        db.flush()
        invite_hash = hashlib.sha256(payload.invite_code.strip().encode("utf-8")).hexdigest()
        claimed = db.query(WebInviteCode).filter(WebInviteCode.code_hash == invite_hash, WebInviteCode.used_by_user_id.is_(None)).update(
            {WebInviteCode.used_by_user_id: user.id, WebInviteCode.used_at: datetime.now(UTC)}, synchronize_session=False)
        if claimed != 1:
            db.rollback()
            raise HTTPException(status_code=403, detail={"key": "auth.invite_invalid"})
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
    return {"id": user.id, "username": user.username, "locale": user.locale}


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
    return {"id": user.id, "username": user.username, "locale": user.locale}


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
