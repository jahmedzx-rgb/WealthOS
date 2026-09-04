"""Add loans

Revision ID: d4a1c87e902b
Revises: b42e7f19c301
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "d4a1c87e902b"
down_revision: Union[str, Sequence[str], None] = "b42e7f19c301"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("lender", sa.String(120), nullable=False),
        sa.Column("loan_type", sa.String(30), nullable=False),
        sa.Column("principal_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("outstanding_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("amount_received", sa.Numeric(18, 2), nullable=False),
        sa.Column("fees", sa.Numeric(18, 2), nullable=False),
        sa.Column("annual_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("term_months", sa.Integer(), nullable=False),
        sa.Column("monthly_payment", sa.Numeric(18, 2), nullable=False),
        sa.Column("first_payment_date", sa.Date(), nullable=False),
        sa.Column("destination_account_code", sa.Integer(), nullable=False),
        sa.Column("liability_account_code", sa.Integer(), nullable=False),
        sa.Column("journal_entry_id", sa.Integer(), sa.ForeignKey("journal_entries.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("loans")
