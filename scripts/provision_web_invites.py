"""One-shot operator command: create ten Web Beta invite codes and print them once."""
import hashlib
import secrets

import app.database.model_registry  # noqa: F401
from app.database.engine import SessionLocal
from app.security.models import WebInviteCode


def main() -> None:
    codes = [secrets.token_urlsafe(24) for _ in range(10)]
    with SessionLocal() as db:
        if db.query(WebInviteCode).count():
            raise SystemExit("Invite codes already exist; refusing to replace them.")
        db.add_all(WebInviteCode(code_hash=hashlib.sha256(code.encode("utf-8")).hexdigest()) for code in codes)
        db.commit()
    print("Store these invite codes securely; they will not be shown again:")
    for code in codes:
        print(code)


if __name__ == "__main__":
    main()
