from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.accounting.models.account import Account
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.schemas.income import IncomeRequest
from app.accounting.services.income_service import IncomeService
from app.database.base import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Account.__table__,
            JournalEntry.__table__,
            JournalLine.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    accounts = [
        Account(
            code=code,
            name=name,
            account_type=account_type,
            normal_balance=normal_balance,
        )
        for code, name, account_type, normal_balance in [
            (1120, "Primary Bank Account", "ASSET", "DEBIT"),
            (4100, "Salary Income", "REVENUE", "CREDIT"),
            (4200, "Rental Income", "REVENUE", "CREDIT"),
            (4300, "Dividend Income", "REVENUE", "CREDIT"),
            (4400, "Interest Income", "REVENUE", "CREDIT"),
            (4500, "Business Income", "REVENUE", "CREDIT"),
            (4900, "Other Income", "REVENUE", "CREDIT"),
        ]
    ]
    session.add_all(accounts)
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.parametrize(
    ("source", "income_code"),
    [
        ("SALARY", 4100),
        ("RENTAL", 4200),
        ("DIVIDEND", 4300),
        ("INTEREST", 4400),
        ("BUSINESS", 4500),
        ("OTHER", 4900),
    ],
)
def test_income_creates_balanced_entry_for_every_visible_type(
    db,
    source,
    income_code,
):
    transaction_date = datetime(2026, 8, 8, 9, 30, tzinfo=UTC)
    entry = IncomeService(db).execute(
        IncomeRequest(
            income_source=source,
            destination_account_code=1120,
            amount=Decimal("1250.75"),
            transaction_date=transaction_date,
            description=f"{source} test income",
            linked_source="Test reference",
        )
    )

    lines = (
        db.query(JournalLine)
        .filter(JournalLine.journal_entry_id == entry.id)
        .all()
    )
    accounts_by_id = {
        account.id: account.code
        for account in db.query(Account).all()
    }

    assert entry.transaction_date.replace(tzinfo=UTC) == transaction_date
    assert entry.related_reference == "Test reference"
    assert len(lines) == 2
    assert sum(line.debit for line in lines) == Decimal("1250.75")
    assert sum(line.credit for line in lines) == Decimal("1250.75")
    assert any(
        accounts_by_id[line.account_id] == 1120
        and line.debit == Decimal("1250.75")
        for line in lines
    )
    assert any(
        accounts_by_id[line.account_id] == income_code
        and line.credit == Decimal("1250.75")
        for line in lines
    )


def test_any_income_source_can_use_an_accounting_category(db):
    entry = IncomeService(db).execute(
        IncomeRequest(
            income_source="Creator platform payout",
            accounting_category="BUSINESS",
            destination_account_code=1120,
            amount=Decimal("875.00"),
            transaction_date=datetime(2026, 8, 9, 10, 0, tzinfo=UTC),
            description="Global creator platform payout",
        )
    )

    lines = db.query(JournalLine).filter(
        JournalLine.journal_entry_id == entry.id
    ).all()
    accounts_by_id = {
        account.id: account.code
        for account in db.query(Account).all()
    }

    assert any(
        accounts_by_id[line.account_id] == 4500
        and line.credit == Decimal("875.00")
        for line in lines
    )
