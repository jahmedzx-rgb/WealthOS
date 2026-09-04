"""Seed initial Saudi Exchange securities

Revision ID: b84d2f06a913
Revises: a73b8c91f204
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b84d2f06a913"
down_revision: Union[str, Sequence[str], None] = "a73b8c91f204"
branch_labels = None
depends_on = None

SECURITIES = (
    ("1120", "1120.SR", "Al Rajhi Bank"),
    ("1180", "1180.SR", "Saudi National Bank"),
    ("2010", "2010.SR", "SABIC"),
    ("2222", "2222.SR", "Saudi Aramco"),
    ("7010", "7010.SR", "stc"),
)


def upgrade() -> None:
    connection = op.get_bind()
    for symbol, market_symbol, name in SECURITIES:
        connection.execute(
            sa.text(
            "INSERT INTO securities (symbol, market_symbol, name, security_type, exchange, currency_code, is_active) "
            "SELECT :symbol, :market_symbol, :name, 'STOCK', 'SAUDI_EXCHANGE', 'SAR', true "
            "WHERE NOT EXISTS (SELECT 1 FROM securities WHERE symbol = :symbol)"
            ),
            {"symbol": symbol, "market_symbol": market_symbol, "name": name},
        )


def downgrade() -> None:
    connection = op.get_bind()
    for symbol, _, _ in SECURITIES:
        connection.execute(
            sa.text(
                "DELETE FROM securities WHERE symbol = :symbol "
                "AND NOT EXISTS (SELECT 1 FROM positions WHERE security_id = securities.id)"
            ),
            {"symbol": symbol},
        )
