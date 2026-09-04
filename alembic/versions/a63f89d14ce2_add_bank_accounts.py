"""add bank accounts

Revision ID: a63f89d14ce2
Revises: f4a71c8d092b
"""
from alembic import op
import sqlalchemy as sa

revision = "a63f89d14ce2"
down_revision = "f4a71c8d092b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("bank_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bank_name", sa.String(120), nullable=False),
        sa.Column("account_type", sa.String(40), nullable=False),
        sa.Column("account_name", sa.String(120), nullable=False),
        sa.Column("account_identifier", sa.String(64), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False, server_default="SAR"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "account_identifier", name="uq_user_bank_account_identifier"))
    op.create_index("ix_bank_accounts_user_id", "bank_accounts", ["user_id"])


def downgrade():
    op.drop_table("bank_accounts")
