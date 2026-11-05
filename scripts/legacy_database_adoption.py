import hashlib
import os
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import uuid
import re

from alembic import command
from alembic.config import Config
from scripts.managed_files import register_managed_file


USER_ACTIVITY_TABLES = frozenset(
    {
        "alternative_investments",
        "bank_accounts",
        "bank_cards",
        "credit_card_accounts",
        "deposits",
        "import_batches",
        "imported_operations",
        "journal_entries",
        "journal_lines",
        "loans",
        "market_prices",
        "month_closes",
        "portfolio_valuation_snapshots",
        "positions",
        "property_assets",
        "rental_schedules",
        "saving_circles",
        "trades",
    }
)
LEGACY_PROFILE_PATTERN = re.compile(r"Beta-[0-9]{2}")


def find_beta_profile_candidates(application_root: Path) -> list[Path]:
    """Discover prior beta databases without copying, staging, or activating them."""
    candidates = []
    if not application_root.is_dir() or application_root.is_symlink():
        return candidates
    for profile in application_root.iterdir():
        if not profile.is_dir() or profile.is_symlink() or not LEGACY_PROFILE_PATTERN.fullmatch(profile.name):
            continue
        canonical = profile / "data" / "wealthos.db"
        legacy = profile / "wealthos.db"
        source = canonical if canonical.is_file() else legacy
        if source.is_file() and not source.is_symlink():
            candidates.append(source)
    return candidates


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified_sqlite_backup(
    source: Path, destination: Path, *, require_foreign_key_integrity: bool = True
) -> None:
    with closing(sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)) as source_db:
        with closing(sqlite3.connect(destination)) as destination_db:
            source_db.backup(destination_db)
            if destination_db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("The legacy database backup failed its integrity check.")
            if require_foreign_key_integrity and destination_db.execute("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("The legacy database backup has foreign-key violations.")


def _contains_user_activity(database: Path) -> bool:
    with closing(sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("A coexisting WealthOS database failed its integrity check.")
        available = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        return any(
            connection.execute(f'SELECT 1 FROM "{table}" LIMIT 1').fetchone()
            for table in USER_ACTIVITY_TABLES.intersection(available)
        )


def adopt_legacy_database(beta_root: Path, alembic_ini: Path, migration_root: Path) -> bool:
    legacy = beta_root / "wealthos.db"
    canonical = beta_root / "data" / "wealthos.db"
    if legacy.exists() and canonical.exists():
        if not legacy.is_file() or legacy.is_symlink() or not canonical.is_file() or canonical.is_symlink():
            raise RuntimeError("A coexisting WealthOS database path is unsafe.")
        if _contains_user_activity(legacy):
            raise RuntimeError(
                "Both legacy and canonical WealthOS databases contain a legacy database with "
                "financial activity. Automatic merge is disabled; preserve both files and "
                "request recovery review."
            )

        # Early beta builds could leave an unused, seed-only database at the old
        # root after a canonical database had already been created. Preserve a
        # verified copy and archive that inactive legacy file so startup can use
        # the canonical database without deleting or merging either history.
        backup_root = beta_root / "backups"
        token = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex}"
        verified_backup = backup_root / f"inactive-legacy-pre-archive-{token}.db"
        archived_original = backup_root / f"inactive-legacy-original-{token}.db"
        _verified_sqlite_backup(
            legacy, verified_backup, require_foreign_key_integrity=False
        )
        os.replace(legacy, archived_original)
        register_managed_file(beta_root, verified_backup)
        register_managed_file(beta_root, archived_original)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(f"{legacy}{suffix}")
            if sidecar.exists():
                os.replace(sidecar, backup_root / f"inactive-legacy-original-{token}.db{suffix}")
        return True
    if not legacy.exists():
        return False
    if not legacy.is_file() or legacy.is_symlink():
        raise RuntimeError("The legacy WealthOS database path is unsafe.")

    backup_root = beta_root / "backups"
    state_root = beta_root / "state"
    token = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex}"
    verified_backup = backup_root / f"legacy-pre-adoption-{token}.db"
    staged = state_root / f"legacy-adoption-{token}.db"
    archived_original = backup_root / f"legacy-original-{token}.db"

    _verified_sqlite_backup(legacy, verified_backup)
    _verified_sqlite_backup(legacy, staged)
    if _sha256(verified_backup) != _sha256(staged):
        raise RuntimeError("The staged legacy database does not match its verified backup.")

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", migration_root.as_posix())
    config.set_main_option("sqlalchemy.url", f"sqlite:///{staged.as_posix()}")
    config.attributes["database_url_override"] = f"sqlite:///{staged.as_posix()}"
    command.stamp(config, "head")
    command.check(config)

    canonical.parent.mkdir(exist_ok=True)
    os.replace(staged, canonical)
    os.replace(legacy, archived_original)
    register_managed_file(beta_root, verified_backup)
    register_managed_file(beta_root, archived_original)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{legacy}{suffix}")
        if sidecar.exists():
            os.replace(sidecar, backup_root / f"legacy-original-{token}.db{suffix}")
    return True


def adopt_beta_profile_database(
    instance_root: Path, alembic_ini: Path, migration_root: Path
) -> bool:
    """Copy one unambiguous prior Beta-XX database; never modify its source."""
    canonical = instance_root / "data" / "wealthos.db"
    if canonical.exists():
        return False

    application_root = instance_root.parents[1]
    candidates = find_beta_profile_candidates(application_root)

    if not candidates:
        return False
    if len(candidates) != 1:
        raise RuntimeError(
            "Multiple prior beta databases were found. Automatic selection and merge are disabled."
        )

    source = candidates[0]
    token = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex}"
    backup = instance_root / "backups" / f"pre-instance-adoption-{token}.db"
    staged = instance_root / "state" / f"instance-adoption-{token}.db"
    _verified_sqlite_backup(source, backup)
    _verified_sqlite_backup(source, staged)
    if _sha256(backup) != _sha256(staged):
        raise RuntimeError("The prior beta database copy failed hash verification.")

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", migration_root.as_posix())
    config.set_main_option("sqlalchemy.url", f"sqlite:///{staged.as_posix()}")
    config.attributes["database_url_override"] = f"sqlite:///{staged.as_posix()}"
    with closing(sqlite3.connect(staged)) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        stamped = "alembic_version" in tables and connection.execute(
            "SELECT 1 FROM alembic_version LIMIT 1"
        ).fetchone()
    if stamped:
        command.upgrade(config, "head")
    else:
        command.stamp(config, "head")
        command.check(config)

    canonical.parent.mkdir(exist_ok=True)
    os.replace(staged, canonical)
    register_managed_file(instance_root, backup)
    return True
