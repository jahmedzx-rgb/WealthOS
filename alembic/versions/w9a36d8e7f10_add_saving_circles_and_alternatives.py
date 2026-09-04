"""add saving circles and alternative investments

Revision ID: w9a36d8e7f10
Revises: v8f25c7d6e09
"""
from alembic import op
import sqlalchemy as sa

revision = "w9a36d8e7f10"
down_revision = "v8f25c7d6e09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("saving_circles",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform_name", sa.String(120), nullable=False), sa.Column("circle_name", sa.String(140), nullable=False),
        sa.Column("installment_amount", sa.Numeric(18,2), nullable=False), sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("total_installments", sa.Integer(), nullable=False), sa.Column("payout_installment", sa.Integer(), nullable=False),
        sa.Column("installments_paid", sa.Integer(), nullable=False, server_default="0"), sa.Column("amount_received", sa.Numeric(18,2), nullable=False, server_default="0"),
        sa.Column("start_date", sa.Date(), nullable=False), sa.Column("next_payment_date", sa.Date()), sa.Column("payout_date", sa.Date()),
        sa.Column("funding_bank_account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id"), nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_saving_circles_user_id", "saving_circles", ["user_id"])
    op.create_table("alternative_investments",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform_name", sa.String(120), nullable=False), sa.Column("investment_name", sa.String(160), nullable=False), sa.Column("investment_type", sa.String(40), nullable=False),
        sa.Column("funding_bank_account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id"), nullable=False), sa.Column("principal_amount", sa.Numeric(18,2), nullable=False),
        sa.Column("current_value", sa.Numeric(18,2), nullable=False), sa.Column("expected_annual_return", sa.Numeric(8,4), nullable=False, server_default="0"),
        sa.Column("amount_returned", sa.Numeric(18,2), nullable=False, server_default="0"), sa.Column("investment_date", sa.Date(), nullable=False),
        sa.Column("maturity_date", sa.Date()), sa.Column("next_distribution_date", sa.Date()), sa.Column("distribution_frequency", sa.String(24)),
        sa.Column("currency_code", sa.String(3), nullable=False, server_default="SAR"), sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"),
        sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_alternative_investments_user_id", "alternative_investments", ["user_id"])


def downgrade() -> None:
    op.drop_table("alternative_investments")
    op.drop_table("saving_circles")

