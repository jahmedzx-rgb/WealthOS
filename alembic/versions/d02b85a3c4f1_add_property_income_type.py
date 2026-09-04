"""add property income type

Revision ID: d02b85a3c4f1
Revises: c72e5a9b4f10
"""

from alembic import op
import sqlalchemy as sa


revision = "d02b85a3c4f1"
down_revision = "c72e5a9b4f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("property_assets", sa.Column("income_type", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("property_assets", "income_type")
