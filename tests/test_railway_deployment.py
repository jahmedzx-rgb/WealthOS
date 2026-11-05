import os
from unittest.mock import MagicMock

import pytest

from deploy.validate_env import validate_environment


@pytest.fixture
def hosted_environment(monkeypatch):
    values = {
        "WEB_MODE": "true", "DEBUG": "false", "COOKIE_SECURE": "true",
        "DATABASE_URL": "postgresql://localhost/disposable_test",
        "APP_VERSION": "test-release", "MIGRATION_HEAD": "c7e5b0d32a41",
        "TRUSTED_HOSTS": "example.up.railway.app,healthcheck.railway.app",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_valid_hosted_environment(hosted_environment):
    validate_environment()


@pytest.mark.parametrize("key,value", [
    ("WEB_MODE", "false"), ("DEBUG", "true"), ("COOKIE_SECURE", "false"),
    ("DATABASE_URL", "sqlite:///:memory:"), ("MIGRATION_HEAD", "old-head"),
    ("TRUSTED_HOSTS", "*,healthcheck.railway.app"),
    ("TRUSTED_HOSTS", "example.up.railway.app"), ("APP_VERSION", ""),
])
def test_unsafe_hosted_environment_fails_before_connecting(hosted_environment, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError):
        validate_environment()


@pytest.mark.parametrize("heads,expected_status", [(["c7e5b0d32a41"], 200), (["old-head"], 503), ([], 503)])
def test_readiness_checks_database_revision(monkeypatch, heads, expected_status):
    import main
    monkeypatch.setattr(main.settings, "WEB_MODE", True)
    monkeypatch.setenv("MIGRATION_HEAD", "c7e5b0d32a41")
    database = MagicMock()
    database.execute.return_value.scalars.return_value.all.return_value = heads
    factory = MagicMock()
    factory.return_value.__enter__.return_value = database
    monkeypatch.setattr(main, "SessionLocal", factory)
    response = main.ready()
    assert (200 if isinstance(response, dict) else response.status_code) == expected_status
