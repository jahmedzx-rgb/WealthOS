"""add rental schedules

Revision ID: f4c82d1a9e35
Revises: e7b34c19a821
"""
from alembic import op
import sqlalchemy as sa

revision = "f4c82d1a9e35"
down_revision = "e7b34c19a821"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rental_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_reference", sa.String(80), nullable=False),
        sa.Column("property_name", sa.String(160), nullable=False),
        sa.Column("expected_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("next_due_date", sa.Date(), nullable=False),
        sa.Column("destination_account_code", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rental_schedules_user_id", "rental_schedules", ["user_id"])
    op.create_index("ix_rental_schedules_property_reference", "rental_schedules", ["property_reference"])
    op.create_index("ix_rental_schedules_next_due_date", "rental_schedules", ["next_due_date"])


def downgrade() -> None:
    op.drop_table("rental_schedules")
