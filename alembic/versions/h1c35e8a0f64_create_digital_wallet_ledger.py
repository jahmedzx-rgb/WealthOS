"""create dedicated digital wallet ledger

Revision ID: h1c35e8a0f64
Revises: g0b24d7f9e53
"""
from alembic import op

revision = "h1c35e8a0f64"
down_revision = "g0b24d7f9e53"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        INSERT INTO accounts
            (code, name, account_type, normal_balance, parent_id, level, is_header, allow_posting, is_active)
        SELECT 1175, 'Digital Wallets', 'ASSET', 'DEBIT', id, 2, false, true, true
        FROM accounts
        WHERE code = 1100
          AND NOT EXISTS (SELECT 1 FROM accounts WHERE code = 1175)
    """)
    op.execute("""
        UPDATE journal_lines
        SET account_id = (SELECT id FROM accounts WHERE code = 1175)
        WHERE journal_entry_id IN (
            SELECT id FROM journal_entries
            WHERE related_reference LIKE 'opening-digital-wallet:%'
        )
          AND account_id IN (SELECT id FROM accounts WHERE code IN (1120, 1140))
    """)


def downgrade():
    op.execute("""
        UPDATE journal_lines
        SET account_id = (SELECT id FROM accounts WHERE code = 1120)
        WHERE account_id = (SELECT id FROM accounts WHERE code = 1175)
          AND journal_entry_id IN (
              SELECT id FROM journal_entries
              WHERE related_reference LIKE 'opening-digital-wallet:%'
          )
    """)
    op.execute("DELETE FROM accounts WHERE code = 1175")
