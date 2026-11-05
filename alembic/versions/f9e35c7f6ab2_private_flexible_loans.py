"""Private flexible loans and auditable, idempotent events."""
from alembic import op
import sqlalchemy as sa

revision = 'f9e35c7f6ab2'
down_revision = 'e8d24b6e5fa1'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('loans') as batch:
        batch.add_column(sa.Column('private_details', sa.JSON(), nullable=True))
        batch.alter_column('first_payment_date', existing_type=sa.Date(), nullable=True)
    op.create_table('private_loan_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('loan_id', sa.Integer(), sa.ForeignKey('loans.id'), nullable=False),
        sa.Column('kind', sa.String(30), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(18,2), nullable=False),
        sa.Column('journal_entry_id', sa.Integer(), sa.ForeignKey('journal_entries.id'), nullable=True),
        sa.Column('idempotency_key', sa.String(100), nullable=False),
        sa.Column('payload_hash', sa.String(64), nullable=False),
        sa.Column('note', sa.String(500), nullable=False),
        sa.UniqueConstraint('user_id','idempotency_key',name='uq_private_loan_event_key'))

def downgrade():
    # Do not discard private loan history or manufacture payment dates.
    raise RuntimeError('Private loan history requires an explicit data-preserving rollback.')
