"""add setup wizard state

Revision ID: a5f81c2d9e40
Revises: z3e70b1c2d54
"""

from alembic import op
import sqlalchemy as sa


revision = "a5f81c2d9e40"
down_revision = "z3e70b1c2d54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("setup_completed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("preferred_language", sa.String(2), nullable=False, server_default="en"))
    op.add_column("users", sa.Column("base_currency_code", sa.String(3), nullable=False, server_default="SAR"))
    op.add_column("users", sa.Column("enabled_currency_codes", sa.JSON(), nullable=False, server_default='["SAR"]'))
    op.add_column("users", sa.Column("local_data_acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("setup_migration_choice", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("recovery_code_hash", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("security_state_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("failed_unlock_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("next_unlock_allowed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("failed_recovery_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("next_recovery_allowed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("lock_timeout_minutes", sa.Integer(), nullable=False, server_default="15"))


def downgrade() -> None:
    for column in (
        "lock_timeout_minutes",
        "next_recovery_allowed_at",
        "failed_recovery_attempts",
        "next_unlock_allowed_at",
        "failed_unlock_attempts",
        "security_state_version",
        "recovery_code_hash",
        "setup_migration_choice",
        "local_data_acknowledged",
        "enabled_currency_codes",
        "base_currency_code",
        "preferred_language",
        "setup_completed",
    ):
        op.drop_column("users", column)
