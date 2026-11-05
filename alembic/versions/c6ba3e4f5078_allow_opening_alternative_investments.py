"""allow alternative investments without a funding bank account

Revision ID: c6ba3e4f5078
Revises: b5a92d3e4f76
"""

from alembic import op
import sqlalchemy as sa


revision = "c6ba3e4f5078"
down_revision = "b5a92d3e4f76"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("alternative_investments") as batch_op:
        batch_op.alter_column("funding_bank_account_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("alternative_investments") as batch_op:
        batch_op.alter_column("funding_bank_account_id", existing_type=sa.Integer(), nullable=False)
