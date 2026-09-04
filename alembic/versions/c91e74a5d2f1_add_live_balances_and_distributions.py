"""add live balances and investment distributions

Revision ID: c91e74a5d2f1
Revises: b82d617f3a40
"""
from alembic import op
import sqlalchemy as sa

revision = "c91e74a5d2f1"
down_revision = "b82d617f3a40"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("credit_card_accounts", sa.Column("current_balance", sa.Numeric(18, 2), nullable=False, server_default="0"))
    op.add_column("bank_accounts", sa.Column("current_balance", sa.Numeric(18, 2), nullable=False, server_default="0"))
    op.add_column("positions", sa.Column("next_distribution_date", sa.Date(), nullable=True))
    op.add_column("positions", sa.Column("expected_distribution_amount", sa.Numeric(18, 2), nullable=True))
    with op.batch_alter_table("credit_card_accounts") as batch_op:
        batch_op.alter_column("current_balance", existing_type=sa.Numeric(18, 2), server_default=None)
    with op.batch_alter_table("bank_accounts") as batch_op:
        batch_op.alter_column("current_balance", existing_type=sa.Numeric(18, 2), server_default=None)


def downgrade():
    op.drop_column("positions", "expected_distribution_amount")
    op.drop_column("positions", "next_distribution_date")
    op.drop_column("bank_accounts", "current_balance")
    op.drop_column("credit_card_accounts", "current_balance")
