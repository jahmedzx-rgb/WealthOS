"""add one-time web invite codes

Revision ID: d7c13a5d4f93
Revises: c6b02f4c3e82
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "d7c13a5d4f93"
down_revision: str | None = "c6b02f4c3e82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "web_invite_codes",
        sa.Column("code_hash", sa.String(64), primary_key=True),
        sa.Column("used_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("web_invite_codes")
