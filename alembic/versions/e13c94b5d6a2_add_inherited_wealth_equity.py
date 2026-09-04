"""add inherited wealth equity

Revision ID: e13c94b5d6a2
Revises: d02b85a3c4f1
"""

from alembic import op


revision = "e13c94b5d6a2"
down_revision = "d02b85a3c4f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO accounts (code, name, account_type, normal_balance, parent_id, level, is_header, allow_posting, is_active)
        SELECT 3260, 'Inherited Wealth', 'EQUITY', 'CREDIT', NULL, 1, FALSE, TRUE, TRUE
        WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = 3260)
    """)


def downgrade() -> None:
    op.execute("DELETE FROM accounts WHERE code = 3260")
