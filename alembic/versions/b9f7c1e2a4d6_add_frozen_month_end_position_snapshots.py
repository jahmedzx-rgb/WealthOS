"""Persist complete daily and month-end portfolio positions.

Revision ID: b9f7c1e2a4d6
Revises: z3e70b1c2d54
"""
from alembic import op
import sqlalchemy as sa


revision = "b9f7c1e2a4d6"
down_revision = "z3e70b1c2d54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("portfolio_valuation_snapshots") as batch_op:
        batch_op.add_column(sa.Column("positions_snapshot", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("historical_portfolio_ids", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("positions_as_of_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("positions_complete", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("is_month_end", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.alter_column("positions_complete", server_default=None)
        batch_op.alter_column("is_month_end", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("portfolio_valuation_snapshots") as batch_op:
        batch_op.drop_column("is_month_end")
        batch_op.drop_column("positions_complete")
        batch_op.drop_column("positions_as_of_date")
        batch_op.drop_column("historical_portfolio_ids")
        batch_op.drop_column("positions_snapshot")
