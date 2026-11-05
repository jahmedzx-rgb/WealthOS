"""reclassify digital wallet balances

Revision ID: g0b24d7f9e53
Revises: f9a13c6e8d42
"""
from alembic import op

revision = "g0b24d7f9e53"
down_revision = "f9a13c6e8d42"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE journal_lines
        SET account_id = (SELECT id FROM accounts WHERE code = 1140)
        WHERE account_id = (SELECT id FROM accounts WHERE code = 1120)
          AND journal_entry_id IN (
              SELECT id FROM journal_entries
              WHERE related_reference LIKE 'opening-digital-wallet:%'
          )
    """)


def downgrade():
    op.execute("""
        UPDATE journal_lines
        SET account_id = (SELECT id FROM accounts WHERE code = 1120)
        WHERE account_id = (SELECT id FROM accounts WHERE code = 1140)
          AND journal_entry_id IN (
              SELECT id FROM journal_entries
              WHERE related_reference LIKE 'opening-digital-wallet:%'
          )
    """)
