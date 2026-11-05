"""update Manafa website

Revision ID: o8d02f5b7a31
Revises: n7c91e4a6f20
"""
from alembic import op

revision = "o8d02f5b7a31"
down_revision = "n7c91e4a6f20"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE investment_platforms SET website = 'https://manafa.sa' WHERE code = 'MANAFA'")


def downgrade():
    op.execute("UPDATE investment_platforms SET website = 'https://manafa.co' WHERE code = 'MANAFA'")
