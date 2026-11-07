"""Fail closed on unsafe hosted settings, without printing environment values."""

from __future__ import annotations

import os
from urllib.parse import urlsplit

from alembic.config import Config
from alembic.script import ScriptDirectory


def validate_environment() -> None:
    required_flags = {"WEB_MODE": "true", "DEBUG": "false", "COOKIE_SECURE": "true"}
    for key, expected in required_flags.items():
        if os.getenv(key, "").lower() != expected:
            raise RuntimeError(f"Hosted deployment requires {key}={expected}.")
    if os.getenv("WEB_MAX_USERS") != "3":
        raise RuntimeError("Hosted beta registration must be limited to exactly three accounts.")
    for key in ("DATABASE_URL", "MIGRATION_HEAD", "APP_VERSION", "TRUSTED_HOSTS"):
        if not os.getenv(key, "").strip():
            raise RuntimeError(f"Hosted deployment requires {key}.")
    if urlsplit(os.environ["DATABASE_URL"]).scheme != "postgresql":
        raise RuntimeError("Hosted deployment requires a postgresql DATABASE_URL.")
    hosts = [host.strip() for host in os.environ["TRUSTED_HOSTS"].split(",")]
    if any(not host or "*" in host or ":" in host or "/" in host for host in hosts):
        raise RuntimeError("TRUSTED_HOSTS must contain exact hostnames without wildcards or URLs.")
    if "healthcheck.railway.app" not in hosts:
        raise RuntimeError("TRUSTED_HOSTS must include the Railway healthcheck hostname.")
    if not any(host != "healthcheck.railway.app" for host in hosts):
        raise RuntimeError("TRUSTED_HOSTS must also include the application's hostname.")
    heads = ScriptDirectory.from_config(Config("alembic.ini")).get_heads()
    if heads != [os.environ["MIGRATION_HEAD"]]:
        raise RuntimeError("MIGRATION_HEAD does not match the source migration head.")
