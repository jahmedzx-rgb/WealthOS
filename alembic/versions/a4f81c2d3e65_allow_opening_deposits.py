"""allow deposits without a funding bank account

Revision ID: a4f81c2d3e65
Revises: c1368fac9be5
"""

from alembic import op
import sqlalchemy as sa


revision = "a4f81c2d3e65"
down_revision = "c1368fac9be5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("deposits") as batch_op:
        batch_op.alter_column("funding_bank_account_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("deposits") as batch_op:
        batch_op.alter_column("funding_bank_account_id", existing_type=sa.Integer(), nullable=False)
