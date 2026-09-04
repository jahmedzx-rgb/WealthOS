"""Link imported drafts to real posted operations.

Revision ID: t6d03a9b4c87
Revises: s5c92f8a3b76
"""

from alembic import op
import sqlalchemy as sa


revision = "t6d03a9b4c87"
down_revision = "s5c92f8a3b76"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("imported_operations", sa.Column("matched_entity_type", sa.String(length=40), nullable=True))
    op.add_column("imported_operations", sa.Column("matched_entity_id", sa.Integer(), nullable=True))
    op.add_column("imported_operations", sa.Column("posting_reference", sa.String(length=120), nullable=True))
    op.add_column("imported_operations", sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("imported_operations", "posted_at")
    op.drop_column("imported_operations", "posting_reference")
    op.drop_column("imported_operations", "matched_entity_id")
    op.drop_column("imported_operations", "matched_entity_type")
