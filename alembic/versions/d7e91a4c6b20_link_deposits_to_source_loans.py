"""link deposits to source loans

Revision ID: d7e91a4c6b20
Revises: z3e70b1c2d54
"""

from alembic import op
import sqlalchemy as sa

revision = "d7e91a4c6b20"
down_revision = "c6ba3e4f5078"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("deposits") as batch_op:
        batch_op.add_column(sa.Column("source_loan_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("historical_funding_date", sa.Date(), nullable=True))
        batch_op.create_foreign_key("fk_deposits_source_loan_id", "loans", ["source_loan_id"], ["id"], ondelete="SET NULL")

def downgrade() -> None:
    with op.batch_alter_table("deposits") as batch_op:
        batch_op.drop_constraint("fk_deposits_source_loan_id", type_="foreignkey")
        batch_op.drop_column("historical_funding_date")
        batch_op.drop_column("source_loan_id")
