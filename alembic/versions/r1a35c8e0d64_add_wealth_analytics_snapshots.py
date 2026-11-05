"""add wealth analytics snapshots

Revision ID: r1a35c8e0d64
Revises: q0f24b7d9c53
"""
from alembic import op
import sqlalchemy as sa

revision = "r1a35c8e0d64"
down_revision = "q0f24b7d9c53"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "wealth_analytics_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("total_assets", sa.Numeric(20, 2), nullable=False),
        sa.Column("total_liabilities", sa.Numeric(20, 2), nullable=False),
        sa.Column("net_worth", sa.Numeric(20, 2), nullable=False),
        sa.Column("available_cash", sa.Numeric(20, 2), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "snapshot_date", name="uq_wealth_analytics_snapshot_day"),
    )
    op.create_index("ix_wealth_analytics_snapshots_user_id", "wealth_analytics_snapshots", ["user_id"])
    op.create_index("ix_wealth_analytics_snapshots_snapshot_date", "wealth_analytics_snapshots", ["snapshot_date"])


def downgrade():
    op.drop_index("ix_wealth_analytics_snapshots_snapshot_date", table_name="wealth_analytics_snapshots")
    op.drop_index("ix_wealth_analytics_snapshots_user_id", table_name="wealth_analytics_snapshots")
    op.drop_table("wealth_analytics_snapshots")
