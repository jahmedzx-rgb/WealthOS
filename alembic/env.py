from logging.config import fileConfig

# Load the same complete model registry used by the application. Keeping a
# second hand-maintained list here can make Alembic mistake live tables for
# deleted models.
import app.database.model_registry

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

config = context.config

from dotenv import load_dotenv
import os

load_dotenv()

database_url = config.attributes.get("database_url_override") or os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL is required for migrations.")
config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.database.base import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
