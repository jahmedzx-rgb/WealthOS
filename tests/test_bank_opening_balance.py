from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database.model_registry  # noqa: F401
from app.accounting.models import Account, BankAccount, JournalEntry, JournalLine, MonthClose
from app.accounting.schemas.bank_account import BankOpeningBalanceRequest
from app.api.v1.accounting import set_bank_opening_balance
from app.core.models.user import User
from app.database.base import Base


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id=1, email="opening@example.com", full_name="Opening Test")
    bank_ledger = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    opening_equity = Account(code=3150, name="Opening Balance Equity", account_type="EQUITY", normal_balance="CREDIT")
    expense = Account(code=5100, name="Expense", account_type="EXPENSE", normal_balance="DEBIT")
    db.add_all([user, bank_ledger, opening_equity, expense]);db.flush()
    bank = BankAccount(user_id=user.id, bank_name="Bank", account_type="CURRENT", account_name="Primary", account_identifier="SA-OPEN", current_balance=0, currency_code="SAR")
    db.add(bank);db.commit()
    return db,user,bank,bank_ledger,opening_equity,expense


def request(balance: str, opening: datetime, adjustment: datetime | None = None):
    return BankOpeningBalanceRequest(corrected_opening_balance=Decimal(balance), opening_date=opening, adjustment_date=adjustment or opening, reason="Verified statement")


def test_missing_opening_balance_can_be_added_after_account_creation():
    db,user,bank,*_=make_db();opening=datetime(2026,1,2,tzinfo=UTC)
    result=set_bank_opening_balance(bank.id,request("1000",opening),db,user)
    assert result["difference_posted"]==Decimal("1000")
    assert result["current_balance"]==Decimal("1000")
    assert result["prior_period_adjustment"] is False
    assert db.query(JournalEntry).filter_by(related_reference=f"opening-bank-account:{bank.id}").count()==1


def test_correction_posts_only_the_difference_and_preserves_later_transactions():
    db,user,bank,bank_ledger,opening_equity,expense=make_db();opening=datetime(2026,1,2,tzinfo=UTC)
    set_bank_opening_balance(bank.id,request("1000",opening),db,user)
    later=JournalEntry(user_id=user.id,description="Later expense",transaction_date=datetime(2026,1,5,tzinfo=UTC),related_reference="expense:kept")
    db.add(later);db.flush();db.add_all([JournalLine(journal_entry_id=later.id,account_id=expense.id,debit=Decimal("300"),credit=0),JournalLine(journal_entry_id=later.id,account_id=bank_ledger.id,debit=0,credit=Decimal("300"))]);bank.current_balance=Decimal("700");db.commit()
    result=set_bank_opening_balance(bank.id,request("1200",opening,datetime(2026,1,10,tzinfo=UTC)),db,user)
    assert result["difference_posted"]==Decimal("200")
    assert result["current_balance"]==Decimal("900")
    assert db.query(JournalEntry).filter_by(related_reference="expense:kept").one().description=="Later expense"
    corrections=db.query(JournalEntry).filter(JournalEntry.related_reference.startswith(f"opening-bank-account-adjustment:{bank.id}:")).all()
    assert len(corrections)==1
    assert corrections[0].transaction_date.date()==opening.date()


def test_closed_opening_period_uses_visible_current_period_adjustment():
    db,user,bank,*_=make_db();opening=datetime(2026,1,2,tzinfo=UTC);adjustment=datetime(2026,3,4,tzinfo=UTC)
    set_bank_opening_balance(bank.id,request("1000",opening),db,user)
    db.add(MonthClose(user_id=user.id,period_start=date(2026,1,1),period_end=date(2026,1,31),version=1,status="CLOSED",snapshot={},checklist={},checksum="a"*64));db.commit()
    result=set_bank_opening_balance(bank.id,request("900",opening,adjustment),db,user)
    assert result["prior_period_adjustment"] is True
    assert result["difference_posted"]==Decimal("-100")
    assert result["current_balance"]==Decimal("900")
    correction=db.query(JournalEntry).filter(JournalEntry.related_reference.startswith(f"opening-bank-account-adjustment:{bank.id}:")).one()
    assert correction.transaction_date.date()==adjustment.date()
