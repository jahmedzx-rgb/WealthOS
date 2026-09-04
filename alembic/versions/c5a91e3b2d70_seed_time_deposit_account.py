"""seed time deposit ledger account

Revision ID: c5a91e3b2d70
Revises: a4d8127f0c9e
"""
from alembic import op

revision = "c5a91e3b2d70"
down_revision = "a4d8127f0c9e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO accounts (code, name, account_type, normal_balance, parent_id, level, is_header, allow_posting, is_active)
        SELECT 1160, 'Time Deposits', 'ASSET', 'DEBIT', NULL, 1, FALSE, TRUE, TRUE
        WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = 1160)
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM accounts
        WHERE code = 1160
          AND NOT EXISTS (SELECT 1 FROM journal_lines WHERE account_id = accounts.id)
    """)
