"""Add audited scheduled-loan installment payments."""
from alembic import op
import sqlalchemy as sa


revision = "a4c219f8d6b1"
down_revision = "z3e70b1c2d54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loan_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("loan_id", sa.Integer(), sa.ForeignKey("loans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("installment_number", sa.Integer(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("principal_paid", sa.Numeric(18, 2), nullable=False),
        sa.Column("interest_paid", sa.Numeric(18, 2), nullable=False),
        sa.Column("outstanding_after", sa.Numeric(18, 2), nullable=False),
        sa.Column("remaining_installments", sa.Integer(), nullable=False),
        sa.Column("bank_account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id"), nullable=False),
        sa.Column("journal_entry_id", sa.Integer(), sa.ForeignKey("journal_entries.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("note", sa.String(500), nullable=False, server_default=""),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_loan_payment_key"),
        sa.UniqueConstraint("loan_id", "installment_number", name="uq_loan_payment_installment"),
    )
    op.create_index("ix_loan_payments_user_id", "loan_payments", ["user_id"])
    op.create_index("ix_loan_payments_loan_id", "loan_payments", ["loan_id"])


def downgrade() -> None:
    op.drop_index("ix_loan_payments_loan_id", table_name="loan_payments")
    op.drop_index("ix_loan_payments_user_id", table_name="loan_payments")
    op.drop_table("loan_payments")
