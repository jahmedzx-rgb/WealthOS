"""add user tax profile and broker override

Revision ID: o1e58b4c9d32
Revises: n0d47a3b8c21
"""
from alembic import op
import sqlalchemy as sa

revision = "o1e58b4c9d32"
down_revision = "n0d47a3b8c21"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("nationality", sa.String(80), nullable=True))
    op.add_column("users", sa.Column("country_of_residence", sa.String(80), nullable=True))
    op.add_column("users", sa.Column("tax_residence", sa.String(80), nullable=True))
    op.add_column("users", sa.Column("investor_type", sa.String(20), nullable=False, server_default="INDIVIDUAL"))
    op.add_column("users", sa.Column("default_dividend_withholding_tax_rate", sa.Numeric(8, 5), nullable=False, server_default="0"))
    with op.batch_alter_table("brokers") as batch_op:
        batch_op.alter_column("dividend_withholding_tax_rate", existing_type=sa.Numeric(8, 5), nullable=True)
    op.execute("UPDATE brokers SET dividend_withholding_tax_rate = NULL, dividend_withholding_tax_source = 'Investor profile default' WHERE dividend_withholding_tax_rate = 0")


def downgrade():
    op.execute("UPDATE brokers SET dividend_withholding_tax_rate = 0 WHERE dividend_withholding_tax_rate IS NULL")
    with op.batch_alter_table("brokers") as batch_op:
        batch_op.alter_column("dividend_withholding_tax_rate", existing_type=sa.Numeric(8, 5), nullable=False)
    op.drop_column("users", "default_dividend_withholding_tax_rate")
    op.drop_column("users", "investor_type")
    op.drop_column("users", "tax_residence")
    op.drop_column("users", "country_of_residence")
    op.drop_column("users", "nationality")
