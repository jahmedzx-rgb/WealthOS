from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.accounting import adjust_deposit_balance, create_deposit
from app.accounting.models.account import Account
from app.accounting.models.bank_account import BankAccount
from app.accounting.models.deposit import Deposit
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.schemas.deposit import DepositBalanceAdjustmentRequest, DepositRequest
from app.database.base import Base


def test_create_deposit_moves_bank_cash_to_deposit_asset():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, BankAccount.__table__, Deposit.__table__, JournalEntry.__table__, JournalLine.__table__])
    db = sessionmaker(bind=engine)()
    bank_ledger = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    deposit_ledger = Account(code=1160, name="Time Deposits", account_type="ASSET", normal_balance="DEBIT")
    db.add_all([bank_ledger, deposit_ledger]); db.flush()
    bank = BankAccount(user_id=1, bank_name="SNB", account_type="CURRENT", account_name="AlAhli", account_identifier="TEST-1", current_balance=Decimal("15000"), currency_code="SAR")
    db.add(bank); db.commit(); db.refresh(bank)
    request = DepositRequest(provider_name="Dinar", product_name="Monthly Income", product_type="TERM_DEPOSIT", funding_bank_account_id=bank.id, income_bank_account_id=bank.id, principal_amount=Decimal("5000"), annual_return_rate=Decimal("5"), payout_frequency="MONTHLY", start_date=date.today(), maturity_date=date.today()+timedelta(days=365), auto_renew=False, currency_code="SAR", transaction_date=datetime.now(UTC))

    result = create_deposit(request, db, SimpleNamespace(id=1))

    db.refresh(bank)
    assert Decimal(result["current_balance"]) == Decimal("5000")
    assert bank.current_balance == Decimal("10000")
    entry = db.query(JournalEntry).one()
    lines = db.query(JournalLine).order_by(JournalLine.id).all()
    assert entry.related_reference == f"deposit:{result['id']}"
    assert lines[0].debit == Decimal("5000") and lines[0].credit == Decimal("0")
    assert lines[1].debit == Decimal("0") and lines[1].credit == Decimal("5000")


def test_deposit_balance_correction_returns_difference_to_funding_bank():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, BankAccount.__table__, Deposit.__table__, JournalEntry.__table__, JournalLine.__table__])
    db = sessionmaker(bind=engine)()
    bank_ledger = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    deposit_ledger = Account(code=1160, name="Time Deposits", account_type="ASSET", normal_balance="DEBIT")
    db.add_all([bank_ledger, deposit_ledger]); db.flush()
    bank = BankAccount(user_id=1, bank_name="SNB", account_type="CURRENT", account_name="AlAhli", account_identifier="TEST-2", current_balance=Decimal("0"), currency_code="SAR")
    db.add(bank); db.flush()
    deposit = Deposit(user_id=1, provider_name="Wadaie", product_name="Monthly Deposit", product_type="TERM_DEPOSIT", funding_bank_account_id=bank.id, income_bank_account_id=bank.id, principal_amount=Decimal("15000"), current_balance=Decimal("15000"), annual_return_rate=Decimal("4.8"), payout_frequency="MONTHLY", start_date=date.today(), maturity_date=date.today()+timedelta(days=41), auto_renew=False, currency_code="SAR", status="ACTIVE")
    db.add(deposit); db.commit(); db.refresh(deposit)

    result = adjust_deposit_balance(deposit.id, DepositBalanceAdjustmentRequest(corrected_balance=Decimal("10000"), adjustment_date=datetime.now(UTC), reason="Correct original amount"), db, SimpleNamespace(id=1))

    db.refresh(bank)
    assert Decimal(result["current_balance"]) == Decimal("10000")
    assert Decimal(result["principal_amount"]) == Decimal("10000")
    assert bank.current_balance == Decimal("5000")
    entry = db.query(JournalEntry).one()
    lines = db.query(JournalLine).order_by(JournalLine.id).all()
    assert entry.related_reference == f"deposit-adjustment:{deposit.id}"
    assert lines[0].account_id == bank_ledger.id and lines[0].debit == Decimal("5000")
    assert lines[1].account_id == deposit_ledger.id and lines[1].credit == Decimal("5000")
