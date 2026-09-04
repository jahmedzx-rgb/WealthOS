"""add portfolio cash balance

Revision ID: j6f03c9d4e87
Revises: i5e92b8c3d76
"""
from alembic import op
import sqlalchemy as sa

revision = "j6f03c9d4e87"
down_revision = "i5e92b8c3d76"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("portfolios", sa.Column("cash_balance", sa.Numeric(18, 2), nullable=False, server_default="0"))
    op.execute("""
        UPDATE portfolios
        SET cash_balance = COALESCE((
            SELECT SUM(CASE WHEN t.side = 'SELL' THEN t.quantity * t.price - t.commission ELSE -(t.quantity * t.price + t.commission) END)
            FROM trades t WHERE t.portfolio_id = portfolios.id
        ), 0)
    """)
    with op.batch_alter_table("portfolios") as batch_op:
        batch_op.alter_column("cash_balance", existing_type=sa.Numeric(18, 2), server_default=None)


def downgrade():
    op.drop_column("portfolios", "cash_balance")
