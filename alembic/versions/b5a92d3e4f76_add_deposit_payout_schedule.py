"""add deposit payout schedule

Revision ID: b5a92d3e4f76
Revises: a4f81c2d3e65
"""

from alembic import op
import sqlalchemy as sa


revision = "b5a92d3e4f76"
down_revision = "a4f81c2d3e65"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deposits", sa.Column("payout_schedule", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("deposits", "payout_schedule")
