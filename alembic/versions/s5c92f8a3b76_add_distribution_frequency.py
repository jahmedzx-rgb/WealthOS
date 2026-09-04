"""Add inferred distribution frequency to positions.

Revision ID: s5c92f8a3b76
Revises: r4b81e7f2a65
"""

from alembic import op
import sqlalchemy as sa


revision = "s5c92f8a3b76"
down_revision = "r4b81e7f2a65"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("positions", sa.Column("distribution_frequency", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("positions", "distribution_frequency")
