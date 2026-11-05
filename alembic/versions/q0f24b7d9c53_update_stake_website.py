"""update Stake website

Revision ID: q0f24b7d9c53
Revises: p9e13a6c8b42
"""
from alembic import op

revision = "q0f24b7d9c53"
down_revision = "p9e13a6c8b42"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE investment_platforms SET website = 'https://getstake.com/ar/ksa' WHERE code = 'STAKE'")


def downgrade():
    op.execute("UPDATE investment_platforms SET website = 'https://getstake.com' WHERE code = 'STAKE'")
