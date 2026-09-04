"""add broker institution groups and split SNB services

Revision ID: p2f69c5d0e43
Revises: o1e58b4c9d32
"""
from alembic import op
import sqlalchemy as sa

revision = "p2f69c5d0e43"
down_revision = "o1e58b4c9d32"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("brokers", sa.Column("institution_name", sa.String(100), nullable=True))
    op.execute("UPDATE brokers SET institution_name = name")
    op.execute("UPDATE brokers SET name = 'AlAhli Tadawul', institution_name = 'SNB Capital' WHERE lower(name) = 'snb capital'")
    op.execute("UPDATE brokers SET name = 'AlAhli Global', institution_name = 'SNB Capital' WHERE lower(name) = 'snb global'")
    op.execute("""
        INSERT INTO brokers (user_id, code, name, country, website, is_active, commission_rate, commission_source, commission_tax_rate, commission_tax_source, dividend_withholding_tax_rate, dividend_withholding_tax_source, institution_name)
        SELECT b.user_id, 'BRK-SNBG-' || b.user_id, 'AlAhli Global', 'Saudi Arabia', b.website, true, NULL, 'Review broker rate', 15, 'Saudi Arabia standard VAT', b.dividend_withholding_tax_rate, b.dividend_withholding_tax_source, 'SNB Capital'
        FROM brokers b
        WHERE b.name = 'AlAhli Tadawul'
          AND EXISTS (SELECT 1 FROM portfolios p JOIN currencies c ON c.id = p.base_currency_id WHERE p.broker_id = b.id AND c.code <> 'SAR')
          AND NOT EXISTS (SELECT 1 FROM brokers g WHERE g.user_id = b.user_id AND g.name = 'AlAhli Global')
    """)
    op.execute("""
        UPDATE portfolios
        SET broker_id = (
            SELECT g.id
            FROM brokers s
            JOIN brokers g ON g.user_id = s.user_id AND g.name = 'AlAhli Global'
            WHERE s.id = portfolios.broker_id AND s.name = 'AlAhli Tadawul'
        )
        WHERE EXISTS (
            SELECT 1
            FROM brokers s
            JOIN brokers g ON g.user_id = s.user_id AND g.name = 'AlAhli Global'
            JOIN currencies c ON c.id = portfolios.base_currency_id
            WHERE s.id = portfolios.broker_id
              AND s.name = 'AlAhli Tadawul'
              AND c.code <> 'SAR'
        )
    """)


def downgrade():
    op.execute("""
        UPDATE portfolios
        SET broker_id = (
            SELECT s.id
            FROM brokers g
            JOIN brokers s ON s.user_id = g.user_id AND s.name = 'AlAhli Tadawul'
            WHERE g.id = portfolios.broker_id AND g.name = 'AlAhli Global'
        )
        WHERE EXISTS (
            SELECT 1
            FROM brokers g
            JOIN brokers s ON s.user_id = g.user_id AND s.name = 'AlAhli Tadawul'
            WHERE g.id = portfolios.broker_id AND g.name = 'AlAhli Global'
        )
    """)
    op.execute("DELETE FROM brokers WHERE name = 'AlAhli Global' AND code LIKE 'BRK-SNBG-%'")
    op.execute("UPDATE brokers SET name = 'SNB Capital' WHERE name = 'AlAhli Tadawul'")
    op.execute("UPDATE brokers SET name = 'SNB Global' WHERE name = 'AlAhli Global'")
    op.drop_column("brokers", "institution_name")
