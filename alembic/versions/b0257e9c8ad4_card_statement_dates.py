"""Preserve exact card statement dates; do not infer lost historic months."""
from alembic import op
import sqlalchemy as sa
revision = 'b0257e9c8ad4'
down_revision = 'a0146d8a7bc3'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('credit_card_accounts', sa.Column('payment_due_date', sa.Date(), nullable=True))
    op.add_column('credit_card_accounts', sa.Column('statement_cutoff_date', sa.Date(), nullable=True))

def downgrade():
    raise RuntimeError('Explicit data-preserving rollback required for card dates.')
