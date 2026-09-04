"""Add provider-specific market symbol to securities

Revision ID: a73b8c91f204
Revises: e18f7a2b6c44
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a73b8c91f204"
down_revision: Union[str, Sequence[str], None] = "e18f7a2b6c44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("securities", sa.Column("market_symbol", sa.String(length=30), nullable=True))
    op.create_index("ix_securities_market_symbol", "securities", ["market_symbol"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_securities_market_symbol", table_name="securities")
    op.drop_column("securities", "market_symbol")
