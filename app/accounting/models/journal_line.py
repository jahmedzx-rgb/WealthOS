from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class JournalLine(Base):
    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint("debit >= 0", name="ck_journal_lines_debit_nonnegative"),
        CheckConstraint("credit >= 0", name="ck_journal_lines_credit_nonnegative"),
        CheckConstraint(
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
            name="ck_journal_lines_exactly_one_side",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    journal_entry_id: Mapped[int] = mapped_column(
        ForeignKey("journal_entries.id")
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id")
    )

    debit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=0,
    )

    credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=0,
    )

    journal_entry = relationship("JournalEntry")

    account = relationship("Account")
