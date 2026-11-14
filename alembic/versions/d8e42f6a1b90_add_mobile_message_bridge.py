"""Add the secure mobile message bridge.

Revision ID: d8e42f6a1b90
Revises: a1b2c3d4e5f6
"""
from alembic import op
import sqlalchemy as sa


revision = "d8e42f6a1b90"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mobile_pairings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("secret_hash", sa.String(64), nullable=False),
        sa.Column("sender_allowlist", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("secret_hash"),
    )
    op.create_index("ix_mobile_pairings_public_id", "mobile_pairings", ["public_id"], unique=True)
    op.create_index("ix_mobile_pairings_user_id", "mobile_pairings", ["user_id"])
    op.create_table(
        "mobile_devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_name", sa.String(120), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("installation_id", sa.String(120), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("sender_allowlist", sa.JSON(), nullable=False),
        sa.Column("app_version", sa.String(40), nullable=True),
        sa.Column("os_version", sa.String(40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("public_id"),
        sa.UniqueConstraint("token_hash"),
        sa.UniqueConstraint("user_id", "installation_id", name="uq_mobile_device_installation"),
    )
    op.create_index("ix_mobile_devices_public_id", "mobile_devices", ["public_id"], unique=True)
    op.create_index("ix_mobile_devices_user_id", "mobile_devices", ["user_id"])
    op.create_index("ix_mobile_devices_status", "mobile_devices", ["status"])
    op.create_table(
        "mobile_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("mobile_devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.String(160), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("sender", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_operation_id", sa.Integer(), sa.ForeignKey("imported_operations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_id", "source_id", name="uq_mobile_message_source"),
        sa.UniqueConstraint("user_id", "content_hash", name="uq_mobile_message_content"),
    )
    op.create_index("ix_mobile_messages_user_id", "mobile_messages", ["user_id"])
    op.create_index("ix_mobile_messages_device_id", "mobile_messages", ["device_id"])
    op.create_index("ix_mobile_messages_imported_operation_id", "mobile_messages", ["imported_operation_id"])


def downgrade() -> None:
    op.drop_table("mobile_messages")
    op.drop_table("mobile_devices")
    op.drop_table("mobile_pairings")
