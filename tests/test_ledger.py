from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.accounting.models.account import Account
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.database.engine import SessionLocal
from app.accounting.schemas.journal import JournalLineInput
from app.accounting.services.journal_integrity import AccountingSession
from app.accounting.services.ledger_service import LedgerService
from app.core.models.user import User
from app.database.base import Base


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


@pytest.mark.parametrize(
    "lines",
    [
        [JournalLineInput(1, Decimal("0"), Decimal("0")), JournalLineInput(2, Decimal("0"), Decimal("0"))],
        [JournalLineInput(1, Decimal("-1"), Decimal("0")), JournalLineInput(2, Decimal("0"), Decimal("-1"))],
        [JournalLineInput(1, Decimal("1"), Decimal("1")), JournalLineInput(2, Decimal("1"), Decimal("1"))],
        [JournalLineInput(1, Decimal("1"), Decimal("0")), JournalLineInput(2, Decimal("0"), Decimal("2"))],
    ],
)
def test_ledger_rejects_invalid_universal_journal_shapes(lines):
    with pytest.raises(ValueError):
        LedgerService(None).post("Invalid", lines)


def test_commit_boundary_rejects_direct_unbalanced_journal_atomically():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, class_=AccountingSession, autoflush=False)()
    db.add(User(id=1, email="atomic@example.com", full_name="Atomic Test"))
    account = Account(code=1199, name="Atomic Cash", account_type="ASSET", normal_balance="DEBIT")
    db.add(account)
    db.commit()

    entry = JournalEntry(user_id=1, description="Invalid direct write")
    db.add(entry)
    db.flush()
    db.add(JournalLine(journal_entry_id=entry.id, account_id=account.id, debit=Decimal("10"), credit=0))

    with pytest.raises(ValueError, match="at least two lines"):
        db.commit()
    db.rollback()

    assert db.query(JournalEntry).filter_by(description="Invalid direct write").count() == 0
    assert db.query(JournalLine).count() == 0
