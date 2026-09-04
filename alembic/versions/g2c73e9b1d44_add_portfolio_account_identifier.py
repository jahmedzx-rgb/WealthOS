"""add portfolio account identifier

Revision ID: g2c73e9b1d44
Revises: f7a92d6c4b10
"""
from alembic import op
import sqlalchemy as sa

revision = "g2c73e9b1d44"
down_revision = "f7a92d6c4b10"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("portfolios", sa.Column("account_identifier", sa.String(length=80), nullable=True))


def downgrade():
    op.drop_column("portfolios", "account_identifier")
