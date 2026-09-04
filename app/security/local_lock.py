import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError


HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, type=Type.ID)
COMMON_PASSWORDS = frozenset(
    value.casefold()
    for value in (
        "password", "password123", "123456789012", "qwerty123456", "letmein123456",
        "admin12345678", "welcome123456", "iloveyou1234", "wealthos1234",
    )
)


def validate_new_password(value: str) -> None:
    if not 12 <= len(value) <= 256 or len(value.encode("utf-8")) > 1024:
        raise ValueError("The local password must contain 12 to 256 Unicode characters.")
    if value.casefold() in COMMON_PASSWORDS:
        raise ValueError("Choose a less common local password.")


def hash_secret(value: str) -> str:
    return HASHER.hash(value)


def verify_secret(value: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        return bool(HASHER.verify(encoded, value))
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(encoded: str) -> bool:
    try:
        return HASHER.check_needs_rehash(encoded)
    except InvalidHashError:
        return True


def generate_recovery_code() -> str:
    encoded = base64.b32encode(secrets.token_bytes(24)).decode("ascii").rstrip("=")
    return "-".join(encoded[index:index + 4] for index in range(0, len(encoded), 4))


def normalize_recovery_code(value: str) -> str:
    return value.replace("-", "").replace(" ", "").upper()


def session_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def revoke_session(store: dict[str, "UnlockSession"], token: str) -> None:
    if token:
        store.pop(session_token_hash(token), None)


def revoke_user_sessions(store: dict[str, "UnlockSession"], user_id: int) -> None:
    for key, session in list(store.items()):
        if session.user_id == user_id:
            store.pop(key, None)


@dataclass
class UnlockSession:
    user_id: int
    installation_id: str
    principal_sid: str
    security_version: int
    issued_at: datetime
    last_activity_at: datetime
    absolute_expires_at: datetime
    verified_at: datetime


def issue_session(store: dict[str, UnlockSession], *, user_id: int, installation_id: str, principal_sid: str, security_version: int) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    store[session_token_hash(token)] = UnlockSession(user_id, installation_id, principal_sid, security_version, now, now, now + timedelta(hours=12), now)
    return token


def validate_session(store: dict[str, UnlockSession], token: str, *, user_id: int, installation_id: str, principal_sid: str, security_version: int, inactivity_minutes: int, user_activity: bool = False) -> bool:
    key = session_token_hash(token) if token else ""
    session = store.get(key)
    now = datetime.now(UTC)
    valid = bool(
        session
        and session.user_id == user_id
        and hmac.compare_digest(session.installation_id, installation_id)
        and hmac.compare_digest(session.principal_sid, principal_sid)
        and session.security_version == security_version
        and now < session.absolute_expires_at
        and now - session.last_activity_at < timedelta(minutes=inactivity_minutes)
    )
    if not valid:
        store.pop(key, None)
        return False
    if user_activity:
        session.last_activity_at = now
    return True


def recently_verified(store: dict[str, UnlockSession], token: str, *, minutes: int = 5) -> bool:
    session = store.get(session_token_hash(token)) if token else None
    return bool(session and datetime.now(UTC) - session.verified_at <= timedelta(minutes=minutes))
