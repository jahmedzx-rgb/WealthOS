from sqlalchemy.orm import Session

from app.models.journal_entry import JournalEntry


class JournalRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_entry(self, description: str) -> JournalEntry:
        entry = JournalEntry(description=description)

        self.db.add(entry)
        self.db.flush()

        return entry