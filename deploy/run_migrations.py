"""Run the single approved Alembic migration path under a PostgreSQL lock."""

from __future__ import annotations

import os

import psycopg2
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


MIGRATION_LOCK_ID = 905_710_042


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
    finally:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK_ID,))
        finally:
            connection.close()


if __name__ == "__main__":
    main()
