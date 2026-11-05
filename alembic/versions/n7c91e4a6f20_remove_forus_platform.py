"""remove Forus platform

Revision ID: n7c91e4a6f20
Revises: m6b80d3f5e19
"""
from alembic import op

revision = "n7c91e4a6f20"
down_revision = "m6b80d3f5e19"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM investment_platforms WHERE code = 'FORUS'")


def downgrade():
    # Catalog entries are registered by the user, so rollback does not recreate user data.
    pass
