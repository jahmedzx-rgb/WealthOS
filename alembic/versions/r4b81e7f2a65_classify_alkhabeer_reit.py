"""Classify Alkhabeer REIT correctly.

Revision ID: r4b81e7f2a65
Revises: q3a70d6e1f54
"""

from alembic import op


revision = "r4b81e7f2a65"
down_revision = "q3a70d6e1f54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE securities SET security_type = 'REIT' WHERE symbol = '4348' OR market_symbol = '4348.SR'")


def downgrade() -> None:
    pass
