from sqlalchemy.orm import Session

from app.accounting.schemas.journal_entry import (
    JournalEntryRequest,
)
from app.accounting.services.journal_entry_service import (
    JournalEntryService,
)


class JournalEntryUseCase:
    def __init__(self, db: Session, user_id: int = 1):
        self.service = JournalEntryService(db, user_id)

    def execute(
        self,
        request: JournalEntryRequest,
    ):
        return self.service.execute(request)
