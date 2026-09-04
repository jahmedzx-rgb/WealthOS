import os
from pathlib import Path
import sqlite3
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run_upgrade(database: Path, revision: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ROOT / "alembic.ini"), "upgrade", revision],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def current_revision(database: Path) -> str:
    with sqlite3.connect(database) as connection:
        return connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]


def test_empty_sqlite_database_upgrades_from_root_to_head(tmp_path):
    database = tmp_path / "clean.sqlite3"
    run_upgrade(database, "head")
    assert current_revision(database) == "c6b02f4c3e82"


def test_previous_beta_head_upgrades_to_current_head(tmp_path):
    database = tmp_path / "previous-head.sqlite3"
    run_upgrade(database, "z2d69a0b1c43")
    assert current_revision(database) == "z2d69a0b1c43"
    run_upgrade(database, "head")
    assert current_revision(database) == "c6b02f4c3e82"
