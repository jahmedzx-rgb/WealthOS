"""add bank cards

Revision ID: z2d69a0b1c43
Revises: y1c58f0a9b32
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "z2d69a0b1c43"
down_revision: Union[str, Sequence[str], None] = "y1c58f0a9b32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bank_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bank_account_id", sa.Integer(), nullable=False),
        sa.Column("card_name", sa.String(length=120), nullable=False),
        sa.Column("last4", sa.String(length=4), nullable=False),
        sa.Column("card_network", sa.String(length=30), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["bank_account_id"], ["bank_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "bank_account_id", "last4", name="uq_user_bank_card"),
    )
    op.create_index(op.f("ix_bank_cards_bank_account_id"), "bank_cards", ["bank_account_id"], unique=False)
    op.create_index(op.f("ix_bank_cards_user_id"), "bank_cards", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bank_cards_user_id"), table_name="bank_cards")
    op.drop_index(op.f("ix_bank_cards_bank_account_id"), table_name="bank_cards")
    op.drop_table("bank_cards")
