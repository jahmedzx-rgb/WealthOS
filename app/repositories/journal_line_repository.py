from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.journal_line import JournalLine


class JournalLineRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_line(
        self,
        journal_entry_id: int,
        account_id: int,
        debit: Decimal,
        credit: Decimal,
    ) -> JournalLine:

        line = JournalLine(
            journal_entry_id=journal_entry_id,
            account_id=account_id,
            debit=debit,
            credit=credit,
        )

        self.db.add(line)

        return line