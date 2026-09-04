from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.accounting.models.account import Account
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.schemas.card_payment import CardPaymentRequest
from app.accounting.schemas.journal_entry import JournalEntryLineRequest, JournalEntryRequest
from app.accounting.services.card_payment_service import CardPaymentService
from app.accounting.services.journal_entry_service import JournalEntryService
from app.database.base import Base
from app.accounting.models.credit_card_account import CreditCardAccount
from app.accounting.models.bank_account import BankAccount
from app.accounting.application.transfer_service import TransferService
from app.accounting.schemas.transfer import TransferRequest
from app.core.models.user import User


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[User.__table__, Account.__table__, JournalEntry.__table__, JournalLine.__table__, CreditCardAccount.__table__, BankAccount.__table__])
    db = sessionmaker(bind=engine)()
    db.add_all([
        Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=2110, name="Credit Cards", account_type="LIABILITY", normal_balance="CREDIT"),
        Account(code=5100, name="Living Expenses", account_type="EXPENSE", normal_balance="DEBIT"),
    ])
    db.add(User(id=1,email="test@example.com",full_name="Test User"))
    db.add(CreditCardAccount(id=1,user_id=1,issuer_bank="Bank",card_name="Visa",last4="1234",credit_limit=Decimal("5000"),current_balance=Decimal("1000"),statement_balance=Decimal("1000"),minimum_monthly_payment=Decimal("50"),currency_code="SAR"))
    db.add(BankAccount(id=1,user_id=1,bank_name="Bank",account_type="CURRENT",account_name="Primary",account_identifier="SA0001",current_balance=Decimal("2000"),currency_code="SAR"))
    db.commit()
    return db


def test_card_payment_posts_and_uses_requested_date():
    db = make_db(); date = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    entry = CardPaymentService(db).execute(CardPaymentRequest(credit_card_id=1,bank_account_id=1,credit_card_account_code=2110, payment_account_code=1120, amount=Decimal("250"), transaction_date=date, description="Card payment"))
    lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == entry.id).all()
    assert entry.transaction_date.replace(tzinfo=UTC) == date
    assert sum(line.debit for line in lines) == Decimal("250")
    assert sum(line.credit for line in lines) == Decimal("250")
    assert db.get(CreditCardAccount,1).current_balance == Decimal("750")
    assert db.get(CreditCardAccount,1).statement_balance == Decimal("750")
    assert db.get(BankAccount,1).current_balance == Decimal("1750")


def test_manual_journal_commits_and_uses_requested_date():
    db = make_db(); date = datetime(2026, 8, 9, 13, 0, tzinfo=UTC)
    entry = JournalEntryService(db).execute(JournalEntryRequest(transaction_date=date, description="Living expense", lines=[JournalEntryLineRequest(account_code=5100,debit=Decimal("80"),credit=Decimal("0")),JournalEntryLineRequest(account_code=1120,debit=Decimal("0"),credit=Decimal("80"))]))
    db.expire_all()
    saved = db.get(JournalEntry, entry.id)
    assert saved is not None
    assert saved.transaction_date.replace(tzinfo=UTC) == date
    assert db.query(JournalLine).filter(JournalLine.journal_entry_id == entry.id).count() == 2


def test_bank_to_bank_transfer_updates_real_accounts_without_changing_total_cash():
    db = make_db(); date = datetime(2026, 8, 9, 14, 0, tzinfo=UTC)
    db.add(BankAccount(id=2,user_id=1,bank_name="Other Bank",account_type="CURRENT",account_name="Savings",account_identifier="SA0002",current_balance=Decimal("300"),currency_code="SAR")); db.commit()
    entry = TransferService(db, 1).execute(TransferRequest(from_account_code=1120,to_account_code=1120,from_bank_account_id=1,to_bank_account_id=2,amount=Decimal("200"),transaction_date=date,description="Move to savings"))
    lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == entry.id).all()
    assert entry.transaction_date.replace(tzinfo=UTC) == date
    assert sum((line.debit for line in lines), Decimal("0")) == Decimal("200")
    assert sum((line.credit for line in lines), Decimal("0")) == Decimal("200")
    assert db.get(BankAccount,1).current_balance == Decimal("1800")
    assert db.get(BankAccount,2).current_balance == Decimal("500")
