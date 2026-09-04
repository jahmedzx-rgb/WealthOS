"""add deposits

Revision ID: a4d8127f0c9e
Revises: f18a4d260b31
"""
from alembic import op
import sqlalchemy as sa

revision = "a4d8127f0c9e"
down_revision = "f18a4d260b31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deposits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_name", sa.String(120), nullable=False),
        sa.Column("product_name", sa.String(120), nullable=False),
        sa.Column("product_type", sa.String(40), nullable=False),
        sa.Column("funding_bank_account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id"), nullable=False),
        sa.Column("income_bank_account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id"), nullable=True),
        sa.Column("principal_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("current_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("annual_return_rate", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("payout_frequency", sa.String(30), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("currency_code", sa.String(3), nullable=False, server_default="SAR"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deposits_user_id", "deposits", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_deposits_user_id", table_name="deposits")
    op.drop_table("deposits")
