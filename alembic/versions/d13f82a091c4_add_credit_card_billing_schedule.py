"""add credit card billing schedule

Revision ID: d13f82a091c4
Revises: c91e74a5d2f1
"""
from alembic import op
import sqlalchemy as sa

revision = "d13f82a091c4"
down_revision = "c91e74a5d2f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("credit_card_accounts", sa.Column("statement_cutoff_day", sa.Integer(), nullable=True))
    op.add_column("credit_card_accounts", sa.Column("payment_due_day", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("credit_card_accounts", "payment_due_day")
    op.drop_column("credit_card_accounts", "statement_cutoff_day")
