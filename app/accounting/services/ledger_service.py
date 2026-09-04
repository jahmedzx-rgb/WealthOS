from datetime import datetime
from sqlalchemy.orm import Session

from app.accounting.repositories.journal_line_repository import (
    JournalLineRepository,
)
from app.accounting.repositories.journal_repository import JournalRepository
from app.accounting.schemas.journal import JournalLineInput
from app.accounting.services.journal_integrity import validate_lines


class LedgerService:
    def __init__(self, db: Session):
        self.db = db

        self.journal_repository = JournalRepository(db)
        self.journal_line_repository = JournalLineRepository(db)

    def post(
        self,
        description: str,
        lines: list[JournalLineInput],
        user_id: int = 1,
        transaction_date: datetime | None = None,
        related_reference: str | None = None,
    ):
        validate_lines(lines)

        entry = self.journal_repository.create_entry(
            description,
            user_id=user_id,
            transaction_date=transaction_date,
            related_reference=related_reference,
        )

        for line in lines:
            self.journal_line_repository.create_line(
                journal_entry_id=entry.id,
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
            )

        self.db.flush()

        return entry
