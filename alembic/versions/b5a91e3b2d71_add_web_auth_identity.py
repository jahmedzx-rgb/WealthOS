"""add web authentication identity

Revision ID: b5a91e3b2d71
Revises: a4f81c2d9e66
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b5a91e3b2d71"
down_revision: str | None = "a4f81c2d9e66"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("username_normalized", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("locale", sa.String(10), nullable=False, server_default="en"))
    op.create_index("ix_users_username_normalized", "users", ["username_normalized"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username_normalized", table_name="users")
    op.drop_column("users", "locale")
    op.drop_column("users", "username_normalized")
    op.drop_column("users", "username")
