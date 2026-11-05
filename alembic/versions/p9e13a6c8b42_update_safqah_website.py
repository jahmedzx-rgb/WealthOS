"""update Safqah website

Revision ID: p9e13a6c8b42
Revises: o8d02f5b7a31
"""
from alembic import op

revision = "p9e13a6c8b42"
down_revision = "o8d02f5b7a31"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE investment_platforms SET website = 'https://safqah.co' WHERE code = 'SAFQAH'")


def downgrade():
    op.execute("UPDATE investment_platforms SET website = 'https://safqah.sa' WHERE code = 'SAFQAH'")
