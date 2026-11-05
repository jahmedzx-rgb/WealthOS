"""add deposit settlement history

Revision ID: f9a13c6e8d42
Revises: e8f02b5d7c31
"""
from alembic import op
import sqlalchemy as sa

revision = "f9a13c6e8d42"
down_revision = "e8f02b5d7c31"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("deposits") as batch_op:
        batch_op.add_column(sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("settlement_action", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("settlement_bank_account_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("actual_return", sa.Numeric(18, 2), nullable=True))
        batch_op.create_foreign_key("fk_deposits_settlement_bank_account_id", "bank_accounts", ["settlement_bank_account_id"], ["id"], ondelete="SET NULL")


def downgrade():
    with op.batch_alter_table("deposits") as batch_op:
        batch_op.drop_constraint("fk_deposits_settlement_bank_account_id", type_="foreignkey")
        batch_op.drop_column("actual_return")
        batch_op.drop_column("settlement_bank_account_id")
        batch_op.drop_column("settlement_action")
        batch_op.drop_column("settled_at")
