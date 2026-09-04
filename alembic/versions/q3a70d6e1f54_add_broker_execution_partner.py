"""add broker execution partner and split Al Rajhi services

Revision ID: q3a70d6e1f54
Revises: p2f69c5d0e43
"""
from alembic import op
import sqlalchemy as sa

revision = "q3a70d6e1f54"
down_revision = "p2f69c5d0e43"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("brokers", sa.Column("execution_partner", sa.String(100), nullable=True))
    op.execute("UPDATE brokers SET name = 'Al Rajhi Tadawul', institution_name = 'Al Rajhi Capital' WHERE lower(name) = 'al rajhi capital'")
    op.execute("UPDATE brokers SET institution_name = 'Al Rajhi Capital', execution_partner = 'Interactive Brokers (IBKR)' WHERE lower(name) = 'al rajhi global'")


def downgrade():
    op.execute("UPDATE brokers SET name = 'Al Rajhi Capital' WHERE name = 'Al Rajhi Tadawul'")
    op.drop_column("brokers", "execution_partner")
