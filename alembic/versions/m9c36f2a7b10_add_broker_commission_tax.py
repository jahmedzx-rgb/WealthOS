"""add broker commission tax

Revision ID: m9c36f2a7b10
Revises: l8b25e1f6a09
"""
from alembic import op
import sqlalchemy as sa

revision = "m9c36f2a7b10"
down_revision = "l8b25e1f6a09"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("brokers", sa.Column("commission_tax_rate", sa.Numeric(8, 5), nullable=True))
    op.add_column("brokers", sa.Column("commission_tax_source", sa.String(120), nullable=True))
    op.execute("UPDATE brokers SET commission_tax_rate = 15, commission_tax_source = 'Saudi Arabia standard VAT' WHERE lower(name) = 'snb capital'")


def downgrade():
    op.drop_column("brokers", "commission_tax_source")
    op.drop_column("brokers", "commission_tax_rate")
