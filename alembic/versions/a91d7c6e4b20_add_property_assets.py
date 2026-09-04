"""add classified property assets

Revision ID: a91d7c6e4b20
Revises: f4c82d1a9e35
"""
from alembic import op
import sqlalchemy as sa

revision = "a91d7c6e4b20"
down_revision = "f4c82d1a9e35"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "property_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("acquisition_journal_entry_id", sa.Integer(), sa.ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("usage", sa.String(30), nullable=False, server_default="UNSPECIFIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_property_assets_user_id", "property_assets", ["user_id"])


def downgrade() -> None:
    op.drop_table("property_assets")
