"""add opening property contract

Revision ID: e8d24b6e5fa1
Revises: d7c13a5d4f93
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8d24b6e5fa1"
down_revision: str | None = "d7c13a5d4f93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("property_assets") as batch_op:
        batch_op.add_column(sa.Column("acquisition_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("purchase_price", sa.Numeric(18, 2), nullable=True))
        batch_op.add_column(sa.Column("improvement_cost", sa.Numeric(18, 2), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("purchase_price_estimated", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("improvement_cost_estimated", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("opening_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("opening_market_value", sa.Numeric(18, 2), nullable=True))
        batch_op.add_column(sa.Column("market_value_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("market_value_source", sa.String(160), nullable=True))
        batch_op.add_column(sa.Column("market_value_note", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("valuation_journal_entry_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("external_reference", sa.String(120), nullable=True))
        batch_op.create_foreign_key("fk_property_valuation_journal", "journal_entries", ["valuation_journal_entry_id"], ["id"], ondelete="SET NULL")
        batch_op.create_unique_constraint("uq_property_user_external_reference", ["user_id", "external_reference"])
    op.create_table(
        "property_opening_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("property_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("similarity_fingerprint", sa.String(64), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_property_opening_user_idempotency"),
    )
    op.create_index("ix_property_opening_audits_user_id", "property_opening_audits", ["user_id"])
    op.create_index("ix_property_opening_audits_property_id", "property_opening_audits", ["property_id"])
    op.create_index("ix_property_opening_audits_similarity_fingerprint", "property_opening_audits", ["similarity_fingerprint"])


def downgrade() -> None:
    op.drop_table("property_opening_audits")
    with op.batch_alter_table("property_assets") as batch_op:
        batch_op.drop_constraint("uq_property_user_external_reference", type_="unique")
        batch_op.drop_constraint("fk_property_valuation_journal", type_="foreignkey")
        for column in ["external_reference", "valuation_journal_entry_id", "market_value_note", "market_value_source", "market_value_date", "opening_market_value", "opening_date", "improvement_cost_estimated", "purchase_price_estimated", "improvement_cost", "purchase_price", "acquisition_date"]:
            batch_op.drop_column(column)
