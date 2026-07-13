from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class JournalLine(Base):
    __tablename__ = "journal_lines"

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