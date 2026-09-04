"""Add missing finance cost posting account

Revision ID: e18f7a2b6c44
Revises: d4a1c87e902b
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e18f7a2b6c44"
down_revision: Union[str, Sequence[str], None] = "d4a1c87e902b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        INSERT INTO accounts (code, name, account_type, normal_balance, level, is_header, allow_posting, is_active)
        SELECT 5790, 'Other Finance Costs', 'EXPENSE', 'DEBIT', 1, false, true, true
        WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = 5790)
    """))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM accounts WHERE code = 5790 AND NOT EXISTS (SELECT 1 FROM journal_lines WHERE account_id = accounts.id)"))
