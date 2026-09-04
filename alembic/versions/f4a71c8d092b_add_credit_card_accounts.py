"""add credit card accounts

Revision ID: f4a71c8d092b
Revises: e2b5d18c43a1
"""
from alembic import op
import sqlalchemy as sa

revision = "f4a71c8d092b"
down_revision = "e2b5d18c43a1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("credit_card_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("issuer_bank", sa.String(120), nullable=False),
        sa.Column("card_name", sa.String(120), nullable=False),
        sa.Column("last4", sa.String(4), nullable=False),
        sa.Column("credit_limit", sa.Numeric(18, 2), nullable=False),
        sa.Column("minimum_monthly_payment", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("currency_code", sa.String(3), nullable=False, server_default="SAR"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "last4", name="uq_user_credit_card_last4"))
    op.create_index("ix_credit_card_accounts_user_id", "credit_card_accounts", ["user_id"])


def downgrade():
    op.drop_table("credit_card_accounts")
