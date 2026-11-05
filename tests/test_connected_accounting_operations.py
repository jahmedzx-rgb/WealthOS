from datetime import UTC, datetime
from decimal import Decimal

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.accounting.models.account import Account
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.schemas.card_payment import CardPaymentRequest
from app.accounting.schemas.journal_entry import JournalEntryLineRequest, JournalEntryRequest
from app.accounting.services.card_payment_service import CardPaymentService
from app.api.v1.accounting import credit_card_payment_history
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


def test_card_to_card_payment_moves_debt_once_and_preserves_source_statement():
    db = make_db(); date = datetime(2026, 8, 9, 12, 30, tzinfo=UTC)
    db.add(CreditCardAccount(id=2,user_id=1,issuer_bank="Source Bank",card_name="Mastercard",last4="5678",credit_limit=Decimal("5000"),current_balance=Decimal("300"),statement_balance=Decimal("200"),minimum_monthly_payment=Decimal("15"),currency_code="SAR")); db.commit()
    entry = CardPaymentService(db).execute(CardPaymentRequest(credit_card_id=1,bank_account_id=None,payment_credit_card_id=2,credit_card_account_code=2110,payment_account_code=2110,amount=Decimal("1000"),transaction_date=date,description="Card via SADAD"))
    db.expire_all()
    target = db.get(CreditCardAccount, 1); source = db.get(CreditCardAccount, 2)
    assert target.current_balance == Decimal("0")
    assert target.statement_balance == Decimal("0")
    assert source.current_balance == Decimal("1300")
    assert source.statement_balance == Decimal("200")
    assert entry.related_reference == "credit-card-sadad:2:1"
    assert db.query(JournalEntry).filter(JournalEntry.related_reference == "credit-card-sadad:2:1").count() == 1


def test_card_cannot_pay_itself():
    db = make_db(); date = datetime(2026, 8, 9, 12, 45, tzinfo=UTC)
    with pytest.raises(ValueError, match="cannot pay itself"):
        CardPaymentService(db).execute(CardPaymentRequest(credit_card_id=1,bank_account_id=None,payment_credit_card_id=1,credit_card_account_code=2110,payment_account_code=2110,amount=Decimal("100"),transaction_date=date,description="Invalid self payment"))
    assert db.get(CreditCardAccount, 1).current_balance == Decimal("1000")


def test_repeated_card_rotation_keeps_direction_balances_and_histories_consistent():
    db = make_db(); base = datetime(2026, 8, 9, 13, 0, tzinfo=UTC)
    db.add_all([
        CreditCardAccount(id=2,user_id=1,issuer_bank="Bank B",card_name="Card B",last4="2222",credit_limit=Decimal("5000"),current_balance=Decimal("300"),statement_balance=Decimal("200"),minimum_monthly_payment=Decimal("15"),currency_code="SAR"),
        CreditCardAccount(id=3,user_id=1,issuer_bank="Bank C",card_name="Card C",last4="3333",credit_limit=Decimal("6000"),current_balance=Decimal("2000"),statement_balance=Decimal("1500"),minimum_monthly_payment=Decimal("100"),currency_code="SAR"),
    ]); db.commit()
    initial_total = sum((card.current_balance for card in db.query(CreditCardAccount).all()), Decimal("0"))

    movements = [(1,2,Decimal("250")), (2,3,Decimal("400")), (3,1,Decimal("600"))]
    entries = []
    for offset,(target_id,source_id,amount) in enumerate(movements):
        entries.append(CardPaymentService(db).execute(CardPaymentRequest(credit_card_id=target_id,bank_account_id=None,payment_credit_card_id=source_id,credit_card_account_code=2110,payment_account_code=2110,amount=amount,transaction_date=base.replace(minute=offset),description=f"Rotation {offset + 1}")))

    db.expire_all()
    assert db.get(CreditCardAccount, 1).current_balance == Decimal("1350")
    assert db.get(CreditCardAccount, 2).current_balance == Decimal("150")
    assert db.get(CreditCardAccount, 3).current_balance == Decimal("1800")
    assert sum((card.current_balance for card in db.query(CreditCardAccount).all()), Decimal("0")) == initial_total
    assert [entry.related_reference for entry in entries] == ["credit-card-sadad:2:1", "credit-card-sadad:3:2", "credit-card-sadad:1:3"]
    assert db.query(JournalEntry).filter(JournalEntry.related_reference.like("credit-card-sadad:%")).count() == 3

    user = db.get(User, 1)
    card_one = credit_card_payment_history(1, db, user)
    card_two = credit_card_payment_history(2, db, user)
    card_three = credit_card_payment_history(3, db, user)
    assert {(item["role"], item["amount"]) for item in card_one["payments"]} == {("RECEIVED", Decimal("250")), ("FUNDED", Decimal("600"))}
    assert {(item["role"], item["amount"]) for item in card_two["payments"]} == {("FUNDED", Decimal("250")), ("RECEIVED", Decimal("400"))}
    assert {(item["role"], item["amount"]) for item in card_three["payments"]} == {("FUNDED", Decimal("400")), ("RECEIVED", Decimal("600"))}


def test_card_with_zero_balance_can_receive_credit_from_another_card():
    db = make_db(); date = datetime(2026, 8, 9, 14, 0, tzinfo=UTC)
    target = db.get(CreditCardAccount, 1)
    target.current_balance = Decimal("0"); target.statement_balance = Decimal("0")
    db.add(CreditCardAccount(id=2,user_id=1,issuer_bank="SNB",card_name="CASHBACK I",last4="1943",credit_limit=Decimal("4644.05"),current_balance=Decimal("300"),statement_balance=Decimal("200"),minimum_monthly_payment=Decimal("15"),currency_code="SAR")); db.commit()
    initial_total = sum((card.current_balance for card in db.query(CreditCardAccount).all()), Decimal("0"))

    entry = CardPaymentService(db).execute(CardPaymentRequest(credit_card_id=1,bank_account_id=None,payment_credit_card_id=2,credit_card_account_code=2110,payment_account_code=2110,amount=Decimal("4344.05"),transaction_date=date,description="Create card credit via SADAD"))
    db.expire_all()
    target = db.get(CreditCardAccount, 1); source = db.get(CreditCardAccount, 2)
    assert target.current_balance == Decimal("-4344.05")
    assert target.statement_balance == Decimal("0")
    assert source.current_balance == Decimal("4644.05")
    assert source.statement_balance == Decimal("200")
    assert target.current_balance + source.current_balance == initial_total
    assert entry.related_reference == "credit-card-sadad:2:1"


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
