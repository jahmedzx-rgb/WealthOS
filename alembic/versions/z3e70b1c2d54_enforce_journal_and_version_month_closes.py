"""enforce journal lines and version month closes

Revision ID: z3e70b1c2d54
Revises: z2d69a0b1c43
"""

from alembic import op
import sqlalchemy as sa


revision = "z3e70b1c2d54"
down_revision = "z2d69a0b1c43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    invalid_lines = connection.execute(sa.text("""
        SELECT COUNT(*) FROM journal_lines
        WHERE debit < 0 OR credit < 0
           OR NOT ((debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0))
    """)).scalar_one()
    invalid_entries = connection.execute(sa.text("""
        SELECT COUNT(*) FROM (
            SELECT journal_entry_id
            FROM journal_lines
            GROUP BY journal_entry_id
            HAVING COUNT(*) < 2 OR SUM(debit) <= 0 OR SUM(debit) != SUM(credit)
        ) AS invalid
    """)).scalar_one()
    if invalid_lines or invalid_entries:
        raise RuntimeError(
            "Cannot enforce journal integrity: repair invalid journal lines/entries before upgrading."
        )

    with op.batch_alter_table("journal_lines") as batch_op:
        batch_op.create_check_constraint("ck_journal_lines_debit_nonnegative", "debit >= 0")
        batch_op.create_check_constraint("ck_journal_lines_credit_nonnegative", "credit >= 0")
        batch_op.create_check_constraint(
            "ck_journal_lines_exactly_one_side",
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
        )

    with op.batch_alter_table("month_closes") as batch_op:
        batch_op.drop_constraint("uq_month_close_user_period", type_="unique")
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("predecessor_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_month_closes_predecessor_id",
            "month_closes",
            ["predecessor_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_month_close_user_period_version",
            ["user_id", "period_end", "version"],
        )
    with op.batch_alter_table("month_closes") as batch_op:
        batch_op.alter_column("version", existing_type=sa.Integer(), server_default=None)


def downgrade() -> None:
    duplicate_periods = op.get_bind().execute(sa.text("""
        SELECT COUNT(*) FROM (
            SELECT user_id, period_end
            FROM month_closes
            GROUP BY user_id, period_end
            HAVING COUNT(*) > 1
        ) AS duplicates
    """)).scalar_one()
    if duplicate_periods:
        raise RuntimeError("Cannot downgrade while multiple monthly snapshot versions exist.")

    with op.batch_alter_table("month_closes") as batch_op:
        batch_op.drop_constraint("uq_month_close_user_period_version", type_="unique")
        batch_op.drop_constraint("fk_month_closes_predecessor_id", type_="foreignkey")
        batch_op.drop_column("predecessor_id")
        batch_op.drop_column("version")
        batch_op.create_unique_constraint("uq_month_close_user_period", ["user_id", "period_end"])

    with op.batch_alter_table("journal_lines") as batch_op:
        batch_op.drop_constraint("ck_journal_lines_exactly_one_side", type_="check")
        batch_op.drop_constraint("ck_journal_lines_credit_nonnegative", type_="check")
        batch_op.drop_constraint("ck_journal_lines_debit_nonnegative", type_="check")
