"""add deposit promotional rates

Revision ID: i2d46f9b1a75
Revises: h1c35e8a0f64
"""
from alembic import op
import sqlalchemy as sa

revision = "i2d46f9b1a75"
down_revision = "h1c35e8a0f64"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("deposits", sa.Column("promotional_annual_return_rate", sa.Numeric(8, 4), nullable=True))
    op.add_column("deposits", sa.Column("promotional_rate_end_date", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("deposits", "promotional_rate_end_date")
    op.drop_column("deposits", "promotional_annual_return_rate")
