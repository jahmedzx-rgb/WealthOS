import hashlib
import hmac
import unicodedata
from datetime import UTC, datetime, timedelta
import secrets

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.security.models import AuthRateEvent, WebSessionRecord

SESSION_COOKIE = "__Host-wealthos-session"
CSRF_COOKIE = "__Host-wealthos-csrf"


def normalize_username(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def issue_session(db: Session, user_id: int, security_version: int) -> tuple[str, str]:
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    db.add(WebSessionRecord(token_hash=token_digest(token), user_id=user_id, csrf_hash=token_digest(csrf),
                            security_version=security_version,
                            expires_at=datetime.now(UTC) + timedelta(hours=settings.WEB_SESSION_HOURS)))
    db.commit()
    return token, csrf


def get_session(db: Session, token: str) -> WebSessionRecord | None:
    if not token:
        return None
    session = db.get(WebSessionRecord, token_digest(token))
    if session is None:
        return None
    expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        db.delete(session)
        db.commit()
        return None
    return session


def revoke_session(db: Session, token: str) -> None:
    session = get_session(db, token)
    if session is not None:
        db.delete(session)
        db.commit()


def revoke_user_sessions(db: Session, user_id: int) -> None:
    db.query(WebSessionRecord).filter(WebSessionRecord.user_id == user_id).delete(synchronize_session=False)
    db.commit()


def check_rate_limit(db: Session, key: str, limit: int, window_seconds: int) -> None:
    key_hash = token_digest(key)
    cutoff = datetime.now(UTC) - timedelta(seconds=window_seconds)
    db.query(AuthRateEvent).filter(AuthRateEvent.occurred_at <= cutoff).delete(synchronize_session=False)
    count = db.query(AuthRateEvent.id).filter(AuthRateEvent.rate_key_hash == key_hash, AuthRateEvent.occurred_at > cutoff).count()
    if count >= limit:
        db.commit()
        raise HTTPException(status_code=429, detail={"key": "auth.rate_limited"})
    db.add(AuthRateEvent(rate_key_hash=key_hash))
    db.commit()


def client_key(request: Request, action: str) -> str:
    return f"{action}:{request.client.host if request.client else 'unknown'}"


def csrf_is_valid(request: Request, session: WebSessionRecord) -> bool:
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get("x-csrf-token", "")
    return bool(cookie and header and hmac.compare_digest(cookie, header) and hmac.compare_digest(token_digest(cookie), session.csrf_hash))
