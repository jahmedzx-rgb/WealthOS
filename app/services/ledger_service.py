from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.journal_line_repository import (
    JournalLineRepository,
)
from app.repositories.journal_repository import JournalRepository
from app.schemas.journal import JournalLineInput


class LedgerService:
    def __init__(self, db: Session):
        self.db = db

        self.journal_repository = JournalRepository(db)
        self.journal_line_repository = JournalLineRepository(db)

    def post(
        self,
        description: str,
        lines: list[JournalLineInput],
    ):
        if len(lines) < 2:
            raise ValueError(
                "A journal entry must contain at least two lines."
            )

        total_debit = sum(
            (line.debit for line in lines),
            Decimal("0.00"),
        )

        total_credit = sum(
            (line.credit for line in lines),
            Decimal("0.00"),
        )

        if total_debit != total_credit:
            raise ValueError(
                "Journal entry is not balanced."
            )

        entry = self.journal_repository.create_entry(
            description
        )

        for line in lines:
            self.journal_line_repository.create_line(
                journal_entry_id=entry.id,
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
            )

        self.db.commit()

        return entry