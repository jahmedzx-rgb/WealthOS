"""add credit card statement balance

Revision ID: v8f25c7d6e09
Revises: u7e14b6c5d98
"""
from alembic import op
import sqlalchemy as sa

revision = "v8f25c7d6e09"
down_revision = "u7e14b6c5d98"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("credit_card_accounts", sa.Column("statement_balance", sa.Numeric(18, 2), nullable=False, server_default="0"))
    op.execute("UPDATE credit_card_accounts SET statement_balance = current_balance")
    with op.batch_alter_table("credit_card_accounts") as batch_op:
        batch_op.alter_column("statement_balance", existing_type=sa.Numeric(18, 2), server_default=None)


def downgrade() -> None:
    op.drop_column("credit_card_accounts", "statement_balance")
