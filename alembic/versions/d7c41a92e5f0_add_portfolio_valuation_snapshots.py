"""add portfolio valuation snapshots

Revision ID: d7c41a92e5f0
Revises: a9f4c2d7e310
"""
from alembic import op
import sqlalchemy as sa

revision = "d7c41a92e5f0"
down_revision = "a9f4c2d7e310"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_valuation_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("valuation_date", sa.Date(), nullable=False),
        sa.Column("market_value", sa.Numeric(20, 6), nullable=False),
        sa.Column("total_cost", sa.Numeric(20, 6), nullable=False),
        sa.Column("total_return", sa.Numeric(20, 6), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "portfolio_id", "valuation_date", name="uq_portfolio_snapshot_day"),
    )
    op.create_index("ix_portfolio_valuation_snapshots_user_id", "portfolio_valuation_snapshots", ["user_id"])
    op.create_index("ix_portfolio_valuation_snapshots_portfolio_id", "portfolio_valuation_snapshots", ["portfolio_id"])
    op.create_index("ix_portfolio_valuation_snapshots_valuation_date", "portfolio_valuation_snapshots", ["valuation_date"])


def downgrade() -> None:
    op.drop_table("portfolio_valuation_snapshots")
