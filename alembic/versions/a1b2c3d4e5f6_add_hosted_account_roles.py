"""add single admin and invitation account roles

Revision ID: a1b2c3d4e5f6
Revises: c7e5b0d32a41
"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "c7e5b0d32a41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("web_invite_codes", sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index(
        "uq_users_single_admin",
        "users",
        ["is_admin"],
        unique=True,
        postgresql_where=sa.text("is_admin = true"),
        sqlite_where=sa.text("is_admin = 1"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_single_admin", table_name="users")
    op.drop_column("web_invite_codes", "is_admin")
    op.drop_column("users", "is_admin")
