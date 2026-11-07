"""Run the single approved Alembic migration path under a PostgreSQL lock."""

from __future__ import annotations

import hashlib
import os
import json
from pathlib import Path

import psycopg2
from psycopg2 import sql
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from deploy.validate_env import validate_environment


MIGRATION_LOCK_ID = 905_710_042


def _bootstrap_reference_data(connection) -> None:
    """Add missing public catalogs only; never create personal financial rows."""
    catalogs = json.loads(Path(__file__).with_name("reference_data.json").read_text(encoding="utf-8"))
    allowed = {"accounts", "currencies", "portfolio_strategies", "portfolio_objectives"}
    if set(catalogs) != allowed:
        raise RuntimeError("Unexpected reference-data tables.")
    with connection.cursor() as cursor:
        for table, rows in catalogs.items():
            for row in rows:
                columns = list(row)
                statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT (code) DO NOTHING").format(
                    sql.Identifier(table), sql.SQL(",").join(map(sql.Identifier, columns)),
                    sql.SQL(",").join(sql.Placeholder() for _ in columns),
                )
                cursor.execute(statement, [row[column] for column in columns])


def _invite_hashes_from_env() -> list[tuple[str, bool]]:
    admin_code = os.getenv("WEB_ADMIN_INVITE_CODE", "").strip()
    raw = os.getenv("WEB_INVITE_CODES", "")
    member_codes = [value.strip() for value in raw.replace("\n", ",").split(",") if value.strip()]
    if not admin_code and not member_codes:
        return []
    codes = [admin_code, *member_codes]
    if (len(member_codes) != 2 or len(set(codes)) != 3
            or any(len(code) < 16 for code in codes)):
        raise RuntimeError(
            "Configure one WEB_ADMIN_INVITE_CODE and exactly two unique WEB_INVITE_CODES; "
            "all three codes must be at least 16 characters."
        )
    hashes = [(hashlib.sha256(admin_code.encode("utf-8")).hexdigest(), True)]
    hashes.extend((hashlib.sha256(code.encode("utf-8")).hexdigest(), False) for code in member_codes)
    return hashes


def _provision_invites(connection) -> None:
    hashes = _invite_hashes_from_env()
    if not hashes:
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM web_invite_codes")
        if int(cursor.fetchone()[0]) != 0:
            return
        cursor.executemany(
            "INSERT INTO web_invite_codes (code_hash, created_at, is_admin) VALUES (%s, NOW(), %s)",
            hashes,
        )


def main() -> None:
    validate_environment()
    # Reject malformed invite configuration before making any schema changes.
    _invite_hashes_from_env()
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
        # Catalog initialization and invite provisioning are atomic; reruns keep
        # existing rows, including user changes and consumed invitation codes.
        connection.autocommit = False
        try:
            _bootstrap_reference_data(connection)
            _provision_invites(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.autocommit = True
    finally:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK_ID,))
        finally:
            connection.close()


if __name__ == "__main__":
    main()
