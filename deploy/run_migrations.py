"""Run the single approved Alembic migration path under a PostgreSQL lock."""

from __future__ import annotations

import hashlib
import os

import psycopg2
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


MIGRATION_LOCK_ID = 905_710_042


def _invite_hashes_from_env() -> list[str]:
    raw = os.getenv("WEB_INVITE_CODES", "")
    if not raw:
        return []
    codes = [value.strip() for value in raw.replace("\n", ",").split(",") if value.strip()]
    if len(codes) != 10 or len(set(codes)) != 10 or any(len(code) < 16 for code in codes):
        raise RuntimeError("WEB_INVITE_CODES must contain exactly 10 unique codes of at least 16 characters.")
    return [hashlib.sha256(code.encode("utf-8")).hexdigest() for code in codes]


def _provision_invites(connection) -> None:
    hashes = _invite_hashes_from_env()
    if not hashes:
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM web_invite_codes")
        if int(cursor.fetchone()[0]) != 0:
            return
        cursor.executemany("INSERT INTO web_invite_codes (code_hash, created_at) VALUES (%s, NOW())", [(value,) for value in hashes])


def main() -> None:
    alembic_config = Config("alembic.ini")
    source_heads = ScriptDirectory.from_config(alembic_config).get_heads()
    expected_head = os.environ["MIGRATION_HEAD"]
    if source_heads != [expected_head]:
        raise RuntimeError(
            f"Migration head mismatch: expected {expected_head}, found {','.join(source_heads)}"
        )
    database_url = os.environ["DATABASE_URL"]
    connection = psycopg2.connect(database_url)
    connection.autocommit = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", (MIGRATION_LOCK_ID,))
            acquired = bool(cursor.fetchone()[0])
        if not acquired:
            raise RuntimeError("Another WealthOS migration job holds the release lock.")
        command.upgrade(alembic_config, expected_head)
        _provision_invites(connection)
    finally:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK_ID,))
        finally:
            connection.close()


if __name__ == "__main__":
    main()
