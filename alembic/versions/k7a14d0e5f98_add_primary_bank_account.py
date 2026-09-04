"""add primary bank account

Revision ID: k7a14d0e5f98
Revises: j6f03c9d4e87
"""
from alembic import op
import sqlalchemy as sa

revision = "k7a14d0e5f98"
down_revision = "j6f03c9d4e87"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("bank_accounts", sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("""UPDATE bank_accounts SET is_primary = TRUE WHERE bank_accounts.id = (SELECT b2.id FROM bank_accounts b2 WHERE b2.user_id = bank_accounts.user_id ORDER BY b2.created_at, b2.id LIMIT 1)""")
    with op.batch_alter_table("bank_accounts") as batch_op:
        batch_op.alter_column("is_primary", existing_type=sa.Boolean(), server_default=None)


def downgrade():
    op.drop_column("bank_accounts", "is_primary")
