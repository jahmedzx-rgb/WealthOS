"""normalize bank account identifiers without merging historical duplicates

Revision ID: a4f81c2d9e66
Revises: a5f81c2d9e40
"""
from alembic import op
import sqlalchemy as sa


revision = "a4f81c2d9e66"
down_revision = "a5f81c2d9e40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("bank_accounts") as batch_op:
        batch_op.add_column(sa.Column("account_identifier_normalized", sa.String(64), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, user_id, account_identifier FROM bank_accounts")).mappings().all()
    grouped: dict[tuple[int, str], list[int]] = {}
    for row in rows:
        normalized = "".join(str(row["account_identifier"] or "").replace("-", "").split()).upper()
        grouped.setdefault((row["user_id"], normalized), []).append(row["id"])
    for (_, normalized), ids in grouped.items():
        if normalized and len(ids) == 1:
            connection.execute(sa.text("UPDATE bank_accounts SET account_identifier=:raw, account_identifier_normalized=:normalized WHERE id=:id"), {"raw": normalized, "normalized": normalized, "id": ids[0]})

    with op.batch_alter_table("bank_accounts") as batch_op:
        batch_op.drop_constraint("uq_user_bank_account_identifier", type_="unique")
        batch_op.create_unique_constraint("uq_user_bank_account_identifier_normalized", ["user_id", "account_identifier_normalized"])

    op.create_table(
        "bank_account_identifier_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bank_account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_last4", sa.String(4), nullable=False),
        sa.Column("new_last4", sa.String(4), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bank_account_identifier_audits_bank_account_id", "bank_account_identifier_audits", ["bank_account_id"])
    op.create_index("ix_bank_account_identifier_audits_user_id", "bank_account_identifier_audits", ["user_id"])


def downgrade() -> None:
    duplicates = op.get_bind().execute(sa.text("SELECT COUNT(*) FROM (SELECT user_id, account_identifier FROM bank_accounts GROUP BY user_id, account_identifier HAVING COUNT(*) > 1) d")).scalar_one()
    if duplicates:
        raise RuntimeError("Cannot restore the legacy uniqueness constraint while duplicate identifiers exist.")
    op.drop_table("bank_account_identifier_audits")
    with op.batch_alter_table("bank_accounts") as batch_op:
        batch_op.drop_constraint("uq_user_bank_account_identifier_normalized", type_="unique")
        batch_op.drop_column("account_identifier_normalized")
        batch_op.create_unique_constraint("uq_user_bank_account_identifier", ["user_id", "account_identifier"])
