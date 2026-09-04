"""add property lifecycle status

Revision ID: c72e5a9b4f10
Revises: b38e6f1d9a42
"""
from alembic import op
import sqlalchemy as sa

revision="c72e5a9b4f10"
down_revision="b38e6f1d9a42"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("property_assets",sa.Column("status",sa.String(20),nullable=False,server_default="ACTIVE"))

def downgrade():
    op.drop_column("property_assets","status")
