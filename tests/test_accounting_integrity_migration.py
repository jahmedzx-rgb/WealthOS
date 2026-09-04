from alembic.config import Config
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text


def test_accounting_integrity_migration_upgrades_previous_head_schema():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE accounts (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE journal_entries (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id))"))
        connection.execute(text("""
            CREATE TABLE journal_lines (
                id INTEGER PRIMARY KEY,
                journal_entry_id INTEGER NOT NULL REFERENCES journal_entries(id),
                account_id INTEGER NOT NULL REFERENCES accounts(id),
                debit NUMERIC(18, 2) NOT NULL DEFAULT 0,
                credit NUMERIC(18, 2) NOT NULL DEFAULT 0
            )
        """))
        connection.execute(text("""
            CREATE TABLE month_closes (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'CLOSED',
                snapshot JSON NOT NULL,
                checklist JSON NOT NULL,
                checksum VARCHAR(64) NOT NULL,
                closed_at DATETIME NOT NULL,
                reopened_at DATETIME,
                reopen_reason VARCHAR(500),
                CONSTRAINT uq_month_close_user_period UNIQUE (user_id, period_end)
            )
        """))
        connection.execute(text("INSERT INTO users (id) VALUES (1)"))
        connection.execute(text("INSERT INTO month_closes (id, user_id, period_start, period_end, snapshot, checklist, checksum, closed_at) VALUES (1, 1, '2026-08-01', '2026-08-31', '{}', '{}', 'abc', '2026-08-31')"))

        script = ScriptDirectory.from_config(Config("alembic.ini"))
        revision = script.get_revision("z3e70b1c2d54")
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            revision.module.upgrade()

        columns = {column["name"] for column in inspect(connection).get_columns("month_closes")}
        assert {"version", "predecessor_id"}.issubset(columns)
        assert connection.execute(text("SELECT version FROM month_closes WHERE id = 1")).scalar_one() == 1
        checks = {item["name"] for item in inspect(connection).get_check_constraints("journal_lines")}
        assert checks == {
            "ck_journal_lines_credit_nonnegative",
            "ck_journal_lines_debit_nonnegative",
            "ck_journal_lines_exactly_one_side",
        }
