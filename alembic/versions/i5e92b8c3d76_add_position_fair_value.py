"""add position fair value

Revision ID: i5e92b8c3d76
Revises: h4d81a7f2c65
"""
from alembic import op
import sqlalchemy as sa

revision = "i5e92b8c3d76"
down_revision = "h4d81a7f2c65"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("positions", sa.Column("fair_value", sa.Numeric(18, 4), nullable=True))


def downgrade():
    op.drop_column("positions", "fair_value")
