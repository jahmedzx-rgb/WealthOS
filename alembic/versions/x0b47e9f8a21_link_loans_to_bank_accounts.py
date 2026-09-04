"""link loans to real bank accounts

Revision ID: x0b47e9f8a21
Revises: w9a36d8e7f10
"""

from alembic import op
import sqlalchemy as sa


revision = "x0b47e9f8a21"
down_revision = "w9a36d8e7f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("loans", sa.Column("destination_bank_account_id", sa.Integer(), nullable=True))
    with op.batch_alter_table("loans") as batch_op:
        batch_op.create_foreign_key(
            "fk_loans_destination_bank_account",
            "bank_accounts",
            ["destination_bank_account_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("loans") as batch_op:
        batch_op.drop_constraint("fk_loans_destination_bank_account", type_="foreignkey")
        batch_op.drop_column("destination_bank_account_id")
