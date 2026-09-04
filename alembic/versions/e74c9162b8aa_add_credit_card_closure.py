"""add credit card closure

Revision ID: e74c9162b8aa
Revises: d13f82a091c4
"""
from alembic import op
import sqlalchemy as sa

revision = "e74c9162b8aa"
down_revision = "d13f82a091c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("credit_card_accounts", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("credit_card_accounts", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table("credit_card_accounts") as batch_op:
        batch_op.alter_column("is_active", existing_type=sa.Boolean(), server_default=None)


def downgrade() -> None:
    op.drop_column("credit_card_accounts", "closed_at")
    op.drop_column("credit_card_accounts", "is_active")
