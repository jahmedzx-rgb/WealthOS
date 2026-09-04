from sqlalchemy.orm import Session

from app.accounting.schemas.journal import (
    JournalLineInput,
)
from app.accounting.schemas.journal_entry import (
    JournalEntryRequest,
)
from app.accounting.services.account_resolver import (
    AccountResolver,
)
from app.accounting.services.ledger_service import (
    LedgerService,
)


class JournalEntryService:
    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.user_id = user_id
        self.ledger = LedgerService(db)
        self.account_resolver = AccountResolver(db)

    def execute(
        self,
        request: JournalEntryRequest,
    ):
        lines: list[JournalLineInput] = []

        for line in request.lines:
            account = (
                self.account_resolver.get_by_code(
                    line.account_code,
                )
            )

            lines.append(
                JournalLineInput(
                    account_id=account.id,
                    debit=line.debit,
                    credit=line.credit,
                )
            )

        entry = self.ledger.post(
            user_id=self.user_id,
            description=request.description,
            lines=lines,
            transaction_date=request.transaction_date,
            related_reference=request.related_reference,
        )
        self.db.commit()
        self.db.refresh(entry)
        return entry
