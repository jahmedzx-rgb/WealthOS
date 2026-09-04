"""allow consolidated valuation snapshots

Revision ID: e2b5d18c43a1
Revises: d7c41a92e5f0
"""
from alembic import op
import sqlalchemy as sa

revision = "e2b5d18c43a1"
down_revision = "d7c41a92e5f0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("portfolio_valuation_snapshots") as batch_op:
        batch_op.alter_column("portfolio_id", existing_type=sa.Integer(), nullable=True)


def downgrade():
    op.execute("DELETE FROM portfolio_valuation_snapshots WHERE portfolio_id IS NULL")
    with op.batch_alter_table("portfolio_valuation_snapshots") as batch_op:
        batch_op.alter_column("portfolio_id", existing_type=sa.Integer(), nullable=False)
