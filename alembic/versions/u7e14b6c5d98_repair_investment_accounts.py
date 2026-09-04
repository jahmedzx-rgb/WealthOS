"""Repair legacy investment account codes.

Revision ID: u7e14b6c5d98
Revises: t6d03a9b4c87
"""

from alembic import op


revision = "u7e14b6c5d98"
down_revision = "t6d03a9b4c87"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE accounts SET name = 'Crowdfunding Investments' WHERE code = 1380 AND name = 'Other Investments'")
    op.execute(
        """
        INSERT INTO accounts (code, name, account_type, normal_balance, parent_id, level, is_header, allow_posting, is_active)
        SELECT 1390, 'Other Investments', 'ASSET', 'DEBIT', id, 2, false, true, true
        FROM accounts
        WHERE code = 1300
          AND NOT EXISTS (SELECT 1 FROM accounts WHERE code = 1390)
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM accounts WHERE code = 1390 AND name = 'Other Investments'")
    op.execute("UPDATE accounts SET name = 'Other Investments' WHERE code = 1380 AND name = 'Crowdfunding Investments'")
