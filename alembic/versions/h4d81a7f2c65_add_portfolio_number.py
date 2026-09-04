"""add portfolio number

Revision ID: h4d81a7f2c65
Revises: g2c73e9b1d44
"""
from alembic import op
import sqlalchemy as sa

revision = "h4d81a7f2c65"
down_revision = "g2c73e9b1d44"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("portfolios", sa.Column("portfolio_number", sa.String(length=80), nullable=True))


def downgrade():
    op.drop_column("portfolios", "portfolio_number")
