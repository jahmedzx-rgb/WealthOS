"""Add income entry date and related reference

Revision ID: f31bc6ad8102
Revises: b84d2f06a913
Create Date: 2026-08-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f31bc6ad8102"
down_revision: Union[str, Sequence[str], None] = "b84d2f06a913"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "journal_entries",
        sa.Column(
            "transaction_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "journal_entries",
        sa.Column(
            "related_reference",
            sa.String(length=200),
            nullable=True,
        ),
    )
    with op.batch_alter_table("journal_entries") as batch_op:
        batch_op.alter_column(
            "transaction_date",
            existing_type=sa.DateTime(timezone=True),
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table("journal_entries") as batch_op:
        batch_op.drop_column("related_reference")
        batch_op.drop_column("transaction_date")
