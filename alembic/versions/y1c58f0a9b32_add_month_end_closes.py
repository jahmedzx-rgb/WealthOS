"""add month end closes

Revision ID: y1c58f0a9b32
Revises: x0b47e9f8a21
"""

from alembic import op
import sqlalchemy as sa


revision = "y1c58f0a9b32"
down_revision = "x0b47e9f8a21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "month_closes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="CLOSED"),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("checklist", sa.JSON(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopen_reason", sa.String(500), nullable=True),
        sa.UniqueConstraint("user_id", "period_end", name="uq_month_close_user_period"),
    )
    op.create_index("ix_month_closes_user_id", "month_closes", ["user_id"])
    op.create_index("ix_month_closes_period_end", "month_closes", ["period_end"])


def downgrade() -> None:
    op.drop_index("ix_month_closes_period_end", table_name="month_closes")
    op.drop_index("ix_month_closes_user_id", table_name="month_closes")
    op.drop_table("month_closes")
