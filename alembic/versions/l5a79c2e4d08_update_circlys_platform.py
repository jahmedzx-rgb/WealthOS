"""update Circlys platform identity

Revision ID: l5a79c2e4d08
Revises: k4f68b1d3c97
"""
from alembic import op

revision = "l5a79c2e4d08"
down_revision = "k4f68b1d3c97"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE investment_platforms SET name = 'Circlys', name_ar = 'Circlys', "
        "website = 'https://www.circlys.com' WHERE code = 'CIRCLES'"
    )


def downgrade():
    op.execute(
        "UPDATE investment_platforms SET name = 'Saving Circles', name_ar = 'جمعيات الادخار', "
        "website = NULL WHERE code = 'CIRCLES'"
    )
