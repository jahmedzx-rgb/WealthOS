"""Anchor automatic statements to confirmed existing balances."""
from alembic import op
import sqlalchemy as sa
revision = 'c1368fac9be5'
down_revision = 'b0257e9c8ad4'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('credit_card_accounts', sa.Column('auto_statement_started_at', sa.DateTime(timezone=True)))
    op.add_column('credit_card_accounts', sa.Column('auto_statement_opening_balance', sa.Numeric(18,2)))
    op.add_column('credit_card_accounts', sa.Column('auto_statement_opening_due', sa.Numeric(18,2)))
    op.execute('UPDATE credit_card_accounts SET auto_statement_started_at=CURRENT_TIMESTAMP, auto_statement_opening_balance=current_balance, auto_statement_opening_due=statement_balance WHERE is_active=true')

def downgrade():
    raise RuntimeError('Statement baselines require a data-preserving rollback.')
