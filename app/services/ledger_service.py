from sqlalchemy.orm import Session

from app.repositories.journal_repository import JournalRepository


class LedgerService:
    def __init__(self, db: Session):
        self.db = db
        self.journal_repository = JournalRepository(db)

    def post(self, description: str):
        entry = self.journal_repository.create_entry(description)

        self.db.commit()

        return entry