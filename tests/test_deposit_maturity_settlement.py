from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.accounting import list_deposits, reconcile_deposit_return, settle_deposit_maturity, withdraw_from_deposit
from app.accounting.models.account import Account
from app.accounting.models.bank_account import BankAccount
from app.accounting.models.deposit import Deposit
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.schemas.asset_disposition import DepositMaturitySettlementRequest
from app.accounting.schemas.deposit import DepositReturnReconciliationRequest, DepositWithdrawalRequest
from app.core.models.user import User
from app.database.base import Base


def test_maturity_payout_separates_principal_return_from_deposit_income():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id=1, email="deposit-maturity@example.com", full_name="Deposit Test")
    bank_ledger = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    deposit_ledger = Account(code=1160, name="Term Deposits", account_type="ASSET", normal_balance="DEBIT")
    income_ledger = Account(code=4400, name="Interest Income", account_type="REVENUE", normal_balance="CREDIT")
    db.add_all([user, bank_ledger, deposit_ledger, income_ledger]); db.flush()
    bank = BankAccount(user_id=1, bank_name="SNB", account_type="CURRENT", account_name="Current", account_identifier="7304", current_balance=Decimal("275.00"), currency_code="SAR")
    deposit = Deposit(user_id=1, provider_name="Wadaie", product_name="Weekly Deposit", product_type="TERM_DEPOSIT", principal_amount=Decimal("14300.00"), current_balance=Decimal("14300.00"), annual_return_rate=Decimal("4.10"), payout_frequency="AT_MATURITY", payout_schedule=[], start_date=date(2026, 9, 3), maturity_date=date(2026, 9, 10), auto_renew=False, currency_code="SAR", status="ACTIVE")
    db.add_all([bank, deposit]); db.commit()

    result = settle_deposit_maturity(deposit.id, DepositMaturitySettlementRequest(action="PAYOUT_ALL", destination_bank_account_id=bank.id, actual_return=Decimal("11.40"), transaction_date=datetime(2026, 9, 11, 12, tzinfo=UTC), note="Maturity payout"), db, user)

    db.refresh(bank); db.refresh(deposit)
    assert result["income"] == Decimal("11.40")
    assert bank.current_balance == Decimal("14586.40")
    assert deposit.current_balance == 0
    assert deposit.status == "CLOSED"
    entries = db.query(JournalEntry).order_by(JournalEntry.id).all()
    assert [entry.description for entry in entries] == ["Deposit principal returned · Weekly Deposit", "Deposit income · Weekly Deposit"]
    income_lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == entries[1].id).all()
    assert sum((line.debit for line in income_lines), Decimal("0")) == Decimal("11.40")
    assert sum((line.credit for line in income_lines), Decimal("0")) == Decimal("11.40")


def test_daily_deposit_can_be_closed_with_a_backdated_full_withdrawal():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id=1, email="daily-close@example.com", full_name="Daily Deposit Test")
    bank_ledger = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    deposit_ledger = Account(code=1160, name="Time Deposits", account_type="ASSET", normal_balance="DEBIT")
    income_ledger = Account(code=4400, name="Interest Income", account_type="REVENUE", normal_balance="CREDIT")
    db.add_all([user, bank_ledger, deposit_ledger, income_ledger]); db.flush()
    bank = BankAccount(user_id=1, bank_name="SNB", account_type="CURRENT", account_name="Current", account_identifier="7304", current_balance=Decimal("100.00"), currency_code="SAR")
    deposit = Deposit(user_id=1, provider_name="Wadaie", product_name="Daily Deposit", product_type="INCOME_SAVINGS", principal_amount=Decimal("1000.00"), current_balance=Decimal("1000.00"), annual_return_rate=Decimal("4.00"), payout_frequency="DAILY", payout_schedule=[], start_date=date(2026, 9, 1), maturity_date=None, auto_renew=False, currency_code="SAR", status="ACTIVE")
    db.add_all([bank, deposit]); db.commit()
    closed_at = datetime(2026, 9, 21, 12, tzinfo=UTC)
    reconciled_at = datetime(2026, 9, 10, 12, tzinfo=UTC)

    reconcile_deposit_return(deposit.id, DepositReturnReconciliationRequest(confirmed_balance=Decimal("1001.00"), transaction_date=reconciled_at), db, user)

    result = withdraw_from_deposit(deposit.id, DepositWithdrawalRequest(destination_bank_account_id=bank.id, confirmed_balance=Decimal("1002.25"), amount=Decimal("1002.25"), transaction_date=closed_at, close_deposit=True), db, user)

    db.refresh(bank); db.refresh(deposit)
    assert result["closed"] is True
    assert result["income"] == Decimal("1.25")
    assert bank.current_balance == Decimal("1102.25")
    assert deposit.current_balance == 0
    assert deposit.principal_amount == Decimal("1001.00")
    assert deposit.actual_return == Decimal("2.25")
    assert deposit.status == "CLOSED"
    assert deposit.settled_at == closed_at.replace(tzinfo=None)
    assert deposit.settlement_bank_account_id == bank.id
    history_item = next(item for item in list_deposits(db, user) if item["id"] == deposit.id)
    assert history_item["actual_return"] == Decimal("2.25")
    entries = db.query(JournalEntry).order_by(JournalEntry.id).all()
    assert [entry.transaction_date for entry in entries] == [reconciled_at.replace(tzinfo=None), closed_at.replace(tzinfo=None), closed_at.replace(tzinfo=None)]
    assert [entry.related_reference for entry in entries] == [f"deposit-return:{deposit.id}", f"deposit-return:{deposit.id}", f"deposit-withdrawal:{deposit.id}"]
