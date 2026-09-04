"""add broker commission profile

Revision ID: l8b25e1f6a09
Revises: k7a14d0e5f98
"""
from alembic import op
import sqlalchemy as sa

revision = "l8b25e1f6a09"
down_revision = "k7a14d0e5f98"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("brokers", sa.Column("commission_rate", sa.Numeric(8, 5), nullable=True))
    op.add_column("brokers", sa.Column("commission_source", sa.String(120), nullable=True))
    op.execute("UPDATE brokers SET commission_rate = 0.155, commission_source = 'Saudi Exchange published maximum' WHERE lower(name) = 'snb capital'")


def downgrade():
    op.drop_column("brokers", "commission_source")
    op.drop_column("brokers", "commission_rate")
