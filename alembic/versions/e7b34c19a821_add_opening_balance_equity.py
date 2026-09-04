"""add opening and adjustment equity accounts

Revision ID: e7b34c19a821
Revises: c5a91e3b2d70
"""
from alembic import op

revision = "e7b34c19a821"
down_revision = "c5a91e3b2d70"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO accounts (code, name, account_type, normal_balance, parent_id, level, is_header, allow_posting, is_active)
        SELECT 3150, 'Opening Balance Equity', 'EQUITY', 'CREDIT', NULL, 1, FALSE, TRUE, TRUE
        WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = 3150)
    """)
    op.execute("""
        INSERT INTO accounts (code, name, account_type, normal_balance, parent_id, level, is_header, allow_posting, is_active)
        SELECT 3250, 'Balance Adjustment Equity', 'EQUITY', 'CREDIT', NULL, 1, FALSE, TRUE, TRUE
        WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = 3250)
    """)
    op.execute("""
        UPDATE journal_lines
        SET account_id = (SELECT id FROM accounts WHERE code = 3150)
        WHERE account_id = (SELECT id FROM accounts WHERE code = 3200)
          AND journal_entry_id IN (
            SELECT id FROM journal_entries
            WHERE related_reference LIKE 'bank-account:%' OR related_reference LIKE 'credit-card:%'
          )
    """)
    op.execute("""
        UPDATE journal_lines
        SET account_id = (SELECT id FROM accounts WHERE code = 3250)
        WHERE account_id = (SELECT id FROM accounts WHERE code = 3200)
          AND journal_entry_id IN (
            SELECT id FROM journal_entries WHERE related_reference LIKE 'credit-card-adjustment:%'
          )
    """)


def downgrade() -> None:
    op.execute("UPDATE journal_lines SET account_id = (SELECT id FROM accounts WHERE code = 3200) WHERE account_id IN (SELECT id FROM accounts WHERE code IN (3150, 3250))")
    op.execute("DELETE FROM accounts WHERE code IN (3150, 3250)")
