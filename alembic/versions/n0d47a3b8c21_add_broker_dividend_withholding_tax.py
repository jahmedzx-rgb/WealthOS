"""add broker dividend withholding tax

Revision ID: n0d47a3b8c21
Revises: m9c36f2a7b10
"""
from alembic import op
import sqlalchemy as sa

revision = "n0d47a3b8c21"
down_revision = "m9c36f2a7b10"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("brokers", sa.Column("dividend_withholding_tax_rate", sa.Numeric(8, 5), nullable=False, server_default="0"))
    op.add_column("brokers", sa.Column("dividend_withholding_tax_source", sa.String(120), nullable=True))
    op.execute("UPDATE brokers SET dividend_withholding_tax_source = 'Not applied'")


def downgrade():
    op.drop_column("brokers", "dividend_withholding_tax_source")
    op.drop_column("brokers", "dividend_withholding_tax_rate")
