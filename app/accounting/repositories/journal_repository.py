from datetime import datetime

from sqlalchemy.orm import Session

from app.accounting.models.journal_entry import JournalEntry


class JournalRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_entry(
        self,
        description: str,
        user_id: int = 1,
        transaction_date: datetime | None = None,
        related_reference: str | None = None,
    ) -> JournalEntry:
        entry = JournalEntry(
            description=description,
            user_id=user_id,
            related_reference=related_reference,
        )
        if transaction_date is not None:
            entry.transaction_date = transaction_date

        self.db.add(entry)
        self.db.flush()

        return entry
