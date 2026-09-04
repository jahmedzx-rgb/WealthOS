from pathlib import Path
import sqlite3

import pytest
from sqlalchemy import create_engine

import app.database.model_registry  # noqa: F401
from app.database.base import Base
from scripts.legacy_database_adoption import adopt_beta_profile_database, adopt_legacy_database


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def managed_registry_key(monkeypatch):
    monkeypatch.setattr("scripts.managed_files.load_hmac_key", lambda: b"k" * 32)


def create_unstamped_current_schema(path: Path) -> None:
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    engine.dispose()


def revision(path: Path) -> str:
    with sqlite3.connect(path) as connection:
        return connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]


def test_adopts_verified_legacy_database_when_canonical_is_absent(tmp_path):
    beta_root = tmp_path / "Beta-01"
    for child in ("data", "backups", "diagnostics", "state"):
        (beta_root / child).mkdir(parents=True, exist_ok=True)
    legacy = beta_root / "wealthos.db"
    create_unstamped_current_schema(legacy)

    assert adopt_legacy_database(beta_root, ROOT / "alembic.ini", ROOT / "alembic") is True

    canonical = beta_root / "data" / "wealthos.db"
    assert canonical.is_file()
    assert not legacy.exists()
    assert revision(canonical) == "d7c13a5d4f93"
    assert len(list((beta_root / "backups").glob("legacy-pre-adoption-*.db"))) == 1
    assert len(list((beta_root / "backups").glob("legacy-original-*.db"))) == 1


def test_coexistence_fails_closed_without_modifying_either_database(tmp_path):
    beta_root = tmp_path / "Beta-02"
    (beta_root / "data").mkdir(parents=True)
    legacy = beta_root / "wealthos.db"
    canonical = beta_root / "data" / "wealthos.db"
    create_unstamped_current_schema(legacy)
    create_unstamped_current_schema(canonical)
    with sqlite3.connect(legacy) as connection:
        connection.execute(
            "INSERT INTO users "
            "(id, email, full_name, is_active, created_at, updated_at, investor_type, "
            "default_dividend_withholding_tax_rate) "
            "VALUES (1, 'fixture@example.invalid', 'Fixture', 1, '2026-08-30', "
            "'2026-08-30', 'INDIVIDUAL', 0)"
        )
        connection.execute(
            "INSERT INTO journal_entries "
            "(user_id, description, transaction_date, created_at) "
            "VALUES (1, 'activity', '2026-08-30', '2026-08-30')"
        )

    with pytest.raises(RuntimeError, match="Both legacy and canonical"):
        adopt_legacy_database(beta_root, ROOT / "alembic.ini", ROOT / "alembic")

    assert legacy.is_file()
    assert canonical.is_file()


def test_seed_only_legacy_coexistence_is_archived_and_canonical_is_preserved(tmp_path):
    beta_root = tmp_path / "Beta-08"
    for child in ("data", "backups", "diagnostics", "state"):
        (beta_root / child).mkdir(parents=True, exist_ok=True)
    legacy = beta_root / "wealthos.db"
    canonical = beta_root / "data" / "wealthos.db"
    create_unstamped_current_schema(legacy)
    create_unstamped_current_schema(canonical)
    canonical_hash = canonical.read_bytes()

    assert adopt_legacy_database(beta_root, ROOT / "alembic.ini", ROOT / "alembic") is True

    assert not legacy.exists()
    assert canonical.read_bytes() == canonical_hash
    assert len(list((beta_root / "backups").glob("inactive-legacy-pre-archive-*.db"))) == 1
    assert len(list((beta_root / "backups").glob("inactive-legacy-original-*.db"))) == 1


def test_neutral_instance_copies_one_prior_profile_without_modifying_source(tmp_path):
    application_root = tmp_path / "WealthOS Beta"
    source = application_root / "Beta-08" / "data" / "wealthos.db"
    source.parent.mkdir(parents=True)
    create_unstamped_current_schema(source)
    original = source.read_bytes()
    instance_root = application_root / "instances" / "11111111-1111-4111-8111-111111111111"
    for child in ("data", "backups", "diagnostics", "state"):
        (instance_root / child).mkdir(parents=True, exist_ok=True)

    assert adopt_beta_profile_database(instance_root, ROOT / "alembic.ini", ROOT / "alembic") is True

    assert source.read_bytes() == original
    assert (instance_root / "data" / "wealthos.db").is_file()
    assert revision(instance_root / "data" / "wealthos.db") == "d7c13a5d4f93"
    assert len(list((instance_root / "backups").glob("pre-instance-adoption-*.db"))) == 1


def test_neutral_instance_refuses_multiple_prior_profiles(tmp_path):
    application_root = tmp_path / "WealthOS Beta"
    for name in ("Beta-01", "Beta-08"):
        source = application_root / name / "data" / "wealthos.db"
        source.parent.mkdir(parents=True)
        create_unstamped_current_schema(source)
    instance_root = application_root / "instances" / "22222222-2222-4222-8222-222222222222"
    for child in ("data", "backups", "diagnostics", "state"):
        (instance_root / child).mkdir(parents=True, exist_ok=True)

    with pytest.raises(RuntimeError, match="Multiple prior beta databases"):
        adopt_beta_profile_database(instance_root, ROOT / "alembic.ini", ROOT / "alembic")

    assert not (instance_root / "data" / "wealthos.db").exists()
