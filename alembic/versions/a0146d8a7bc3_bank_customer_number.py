"""Optional bank-level customer numbers, separate from account identifiers."""
from alembic import op
import sqlalchemy as sa
revision='a0146d8a7bc3'
down_revision='f9e35c7f6ab2'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('bank_customers',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('bank_key',sa.String(120),nullable=False),sa.Column('customer_number',sa.String(64),nullable=False),
        sa.UniqueConstraint('user_id','bank_key',name='uq_bank_customer_user_bank'))
def downgrade():
    raise RuntimeError('Customer numbers require an explicit data-preserving rollback.')
