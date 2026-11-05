"""fix Circlys Arabic name

Revision ID: m6b80d3f5e19
Revises: l5a79c2e4d08
"""
from alembic import op

revision = "m6b80d3f5e19"
down_revision = "l5a79c2e4d08"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE investment_platforms SET name_ar = 'سيركليز' WHERE code = 'CIRCLES'")


def downgrade():
    op.execute("UPDATE investment_platforms SET name_ar = 'Circlys' WHERE code = 'CIRCLES'")
