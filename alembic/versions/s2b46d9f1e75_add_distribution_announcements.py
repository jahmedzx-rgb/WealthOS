"""add distribution announcements

Revision ID: s2b46d9f1e75
Revises: r1a35c8e0d64
"""
from alembic import op
import sqlalchemy as sa

revision = "s2b46d9f1e75"
down_revision = "r1a35c8e0d64"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "distribution_announcements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("security_id", sa.Integer(), sa.ForeignKey("securities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fingerprint", sa.String(160), nullable=False),
        sa.Column("announcement_date", sa.Date(), nullable=True),
        sa.Column("eligibility_date", sa.Date(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount_per_unit", sa.Numeric(20, 8), nullable=False),
        sa.Column("eligible_quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("expected_gross_amount", sa.Numeric(20, 2), nullable=False),
        sa.Column("withholding_tax_rate", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("expected_tax_amount", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("expected_net_amount", sa.Numeric(20, 2), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False, server_default="IRREGULAR"),
        sa.Column("source", sa.String(160), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="ANNOUNCED"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "fingerprint", name="uq_distribution_announcement_fingerprint"),
    )
    for column in ("user_id", "portfolio_id", "security_id"):
        op.create_index(f"ix_distribution_announcements_{column}", "distribution_announcements", [column])


def downgrade():
    for column in ("security_id", "portfolio_id", "user_id"):
        op.drop_index(f"ix_distribution_announcements_{column}", table_name="distribution_announcements")
    op.drop_table("distribution_announcements")
