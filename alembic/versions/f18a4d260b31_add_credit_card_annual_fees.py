"""add credit card annual fees

Revision ID: f18a4d260b31
Revises: e74c9162b8aa
"""
from alembic import op
import sqlalchemy as sa

revision = "f18a4d260b31"
down_revision = "e74c9162b8aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("credit_card_accounts", sa.Column("is_fee_free", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("credit_card_accounts", sa.Column("annual_fee", sa.Numeric(18, 2), nullable=False, server_default="0"))
    op.add_column("credit_card_accounts", sa.Column("fee_renewal_day", sa.Integer(), nullable=True))
    op.add_column("credit_card_accounts", sa.Column("fee_renewal_month", sa.Integer(), nullable=True))
    with op.batch_alter_table("credit_card_accounts") as batch_op:
        batch_op.alter_column("is_fee_free", existing_type=sa.Boolean(), server_default=None)
        batch_op.alter_column("annual_fee", existing_type=sa.Numeric(18, 2), server_default=None)


def downgrade() -> None:
    op.drop_column("credit_card_accounts", "fee_renewal_month")
    op.drop_column("credit_card_accounts", "fee_renewal_day")
    op.drop_column("credit_card_accounts", "annual_fee")
    op.drop_column("credit_card_accounts", "is_fee_free")
