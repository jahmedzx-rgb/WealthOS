"""add historical deposit funding amount

Revision ID: e8f02b5d7c31
Revises: d7e91a4c6b20
"""
from alembic import op
import sqlalchemy as sa

revision = "e8f02b5d7c31"
down_revision = "d7e91a4c6b20"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("deposits") as batch_op:
        batch_op.add_column(sa.Column("historical_funding_amount", sa.Numeric(18, 2), nullable=True))


def downgrade():
    with op.batch_alter_table("deposits") as batch_op:
        batch_op.drop_column("historical_funding_amount")
