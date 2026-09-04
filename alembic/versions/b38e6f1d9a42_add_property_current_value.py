"""add current property value

Revision ID: b38e6f1d9a42
Revises: a91d7c6e4b20
"""
from alembic import op
import sqlalchemy as sa

revision = "b38e6f1d9a42"
down_revision = "a91d7c6e4b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("property_assets", sa.Column("current_value", sa.Numeric(18, 2), nullable=True))
    op.execute("""UPDATE property_assets SET current_value = COALESCE((SELECT jl.debit FROM journal_lines jl JOIN accounts a ON a.id = jl.account_id WHERE jl.journal_entry_id = property_assets.acquisition_journal_entry_id AND a.code = 1210 LIMIT 1), 0)""")
    with op.batch_alter_table("property_assets") as batch_op:
        batch_op.alter_column("current_value", existing_type=sa.Numeric(18, 2), nullable=False)


def downgrade() -> None:
    op.drop_column("property_assets", "current_value")
