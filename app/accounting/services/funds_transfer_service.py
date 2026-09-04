from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.schemas.journal import JournalLineInput
from app.accounting.services.ledger_service import (
    LedgerService,
)


class FundsTransferService:
    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.ledger = LedgerService(db)
        self.user_id = user_id

    def execute(
        self,
        from_account_id: int,
        to_account_id: int,
        amount: Decimal,
        description: str,
        transaction_date: datetime | None = None,
        related_reference: str | None = None,
        auto_commit: bool = True,
    ):
        entry = self.ledger.post(
            user_id=self.user_id,
            description=description,
            transaction_date=transaction_date,
            related_reference=related_reference,
            lines=[
                JournalLineInput(
                    account_id=to_account_id,
                    debit=amount,
                    credit=Decimal("0.00"),
                ),
                JournalLineInput(
                    account_id=from_account_id,
                    debit=Decimal("0.00"),
                    credit=amount,
                ),
            ],
        )

        if auto_commit:
            self.db.commit()
            self.db.refresh(entry)
        else:
            self.db.flush()

        return entry
