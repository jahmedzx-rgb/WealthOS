from decimal import Decimal

from app.database.engine import SessionLocal
from app.schemas.journal import JournalLineInput
from app.services.ledger_service import LedgerService


def test_create_journal_entry():
    db = SessionLocal()

    try:
        ledger = LedgerService(db)

        entry = ledger.post(
            description="First WealthOS Journal Entry",
            lines=[
                JournalLineInput(
                    account_id=1,
                    debit=Decimal("1000.00"),
                    credit=Decimal("0.00"),
                ),
                JournalLineInput(
                    account_id=2,
                    debit=Decimal("0.00"),
                    credit=Decimal("1000.00"),
                ),
            ],
        )

        assert entry.id is not None
        assert entry.description == "First WealthOS Journal Entry"

    finally:
        db.close()