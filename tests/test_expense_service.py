from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.accounting.models import Account, BankAccount, JournalEntry, JournalLine, PropertyAsset
from app.accounting.schemas.expense import ExpenseRequest
from app.accounting.services.expense_service import ExpenseService
from app.core.models.user import User
from app.database.base import Base


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[User.__table__, Account.__table__, JournalEntry.__table__, JournalLine.__table__, BankAccount.__table__, PropertyAsset.__table__])
    db = sessionmaker(bind=engine)()
    db.add(User(id=1, email="owner@example.com", full_name="Owner"))
    db.add_all([
        Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=5200, name="Property Expenses", account_type="EXPENSE", normal_balance="DEBIT"),
    ])
    acquisition = JournalEntry(user_id=1, description="Property purchase", transaction_date=datetime(2026, 1, 1, tzinfo=UTC), related_reference="property-purchase")
    db.add(acquisition)
    db.flush()
    db.add(PropertyAsset(id=79, user_id=1, acquisition_journal_entry_id=acquisition.id, name="Semairi Town House", usage="INVESTMENT_PROPERTY", current_value=Decimal("700000"), status="ACTIVE"))
    db.add(BankAccount(id=7, user_id=1, bank_name="SNB", account_type="CURRENT", account_name="Primary", account_identifier="SA001", current_balance=Decimal("1000"), currency_code="SAR", is_primary=True))
    db.commit()
    return db


def test_expense_uses_real_bank_balance_and_links_property():
    db = make_db()
    entry = ExpenseService(db, 1).execute(ExpenseRequest(
        expense_account_code=5200,
        payment_bank_account_id=7,
        property_id=79,
        amount=Decimal("125.50"),
        transaction_date=datetime(2026, 8, 29, 10, 0, tzinfo=UTC),
        description="Air conditioner maintenance",
    ))
    lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == entry.id).all()
    assert entry.related_reference == "property-expense:79"
    assert db.get(BankAccount, 7).current_balance == Decimal("874.50")
    assert sum(line.debit for line in lines) == Decimal("125.50")
    assert sum(line.credit for line in lines) == Decimal("125.50")


def test_expense_rejects_amount_above_selected_bank_balance():
    db = make_db()
    with pytest.raises(ValueError, match="available balance"):
        ExpenseService(db, 1).execute(ExpenseRequest(
            expense_account_code=5200,
            payment_bank_account_id=7,
            property_id=79,
            amount=Decimal("1000.01"),
            transaction_date=datetime(2026, 8, 29, 10, 0, tzinfo=UTC),
            description="Maintenance",
        ))
    assert db.get(BankAccount, 7).current_balance == Decimal("1000")
