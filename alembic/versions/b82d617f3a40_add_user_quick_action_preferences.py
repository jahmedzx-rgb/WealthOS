"""add user quick action preferences

Revision ID: b82d617f3a40
Revises: a63f89d14ce2
"""
from alembic import op
import sqlalchemy as sa

revision = "b82d617f3a40"
down_revision = "a63f89d14ce2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("quick_action_ids", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("users", "quick_action_ids")
