"""persist web authentication state

Revision ID: c6b02f4c3e82
Revises: b5a91e3b2d71
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c6b02f4c3e82"
down_revision: str | None = "b5a91e3b2d71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "web_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("security_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_web_sessions_user_id", "web_sessions", ["user_id"])
    op.create_index("ix_web_sessions_expires_at", "web_sessions", ["expires_at"])
    op.create_table(
        "auth_rate_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rate_key_hash", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_auth_rate_events_rate_key_hash", "auth_rate_events", ["rate_key_hash"])
    op.create_index("ix_auth_rate_events_occurred_at", "auth_rate_events", ["occurred_at"])
    op.create_table(
        "web_registration_slots",
        sa.Column("slot", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.CheckConstraint("slot >= 1 AND slot <= 10", name="ck_web_registration_slot_range"),
    )


def downgrade() -> None:
    op.drop_table("web_registration_slots")
    op.drop_index("ix_auth_rate_events_occurred_at", table_name="auth_rate_events")
    op.drop_index("ix_auth_rate_events_rate_key_hash", table_name="auth_rate_events")
    op.drop_table("auth_rate_events")
    op.drop_index("ix_web_sessions_expires_at", table_name="web_sessions")
    op.drop_index("ix_web_sessions_user_id", table_name="web_sessions")
    op.drop_table("web_sessions")
