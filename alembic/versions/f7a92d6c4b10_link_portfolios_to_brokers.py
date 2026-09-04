"""link portfolios to brokers

Revision ID: f7a92d6c4b10
Revises: e13c94b5d6a2
"""
from alembic import op
import sqlalchemy as sa

revision = "f7a92d6c4b10"
down_revision = "e13c94b5d6a2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("portfolios") as batch_op:
        batch_op.add_column(sa.Column("broker_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_portfolios_broker_id", ["broker_id"], unique=False)
        batch_op.create_foreign_key("fk_portfolios_broker_id_brokers", "brokers", ["broker_id"], ["id"], ondelete="SET NULL")


def downgrade():
    with op.batch_alter_table("portfolios") as batch_op:
        batch_op.drop_constraint("fk_portfolios_broker_id_brokers", type_="foreignkey")
        batch_op.drop_index("ix_portfolios_broker_id")
        batch_op.drop_column("broker_id")
