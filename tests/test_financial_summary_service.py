from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.accounting.models.account import Account
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.models.loan import Loan
from app.accounting.models.credit_card_account import CreditCardAccount
from app.accounting.models.bank_account import BankAccount
from app.accounting.models.deposit import Deposit
from app.accounting.models.property_asset import PropertyAsset
from app.accounting.services.financial_summary_service import FinancialSummaryService
from app.database.base import Base


def test_summary_uses_posted_ledger_balances_and_active_loans():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, JournalEntry.__table__, JournalLine.__table__, Loan.__table__, CreditCardAccount.__table__, BankAccount.__table__, Deposit.__table__, PropertyAsset.__table__])
    db = sessionmaker(bind=engine)()
    bank = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    property_account = Account(code=1210, name="Property", account_type="ASSET", normal_balance="DEBIT")
    liability = Account(code=2220, name="Loan", account_type="LIABILITY", normal_balance="CREDIT")
    credit_card = Account(code=2110, name="Credit Cards", account_type="LIABILITY", normal_balance="CREDIT")
    revenue = Account(code=4100, name="Salary", account_type="REVENUE", normal_balance="CREDIT")
    db.add_all([bank, property_account, liability, credit_card, revenue]); db.flush()
    entry = JournalEntry(description="Current balances", transaction_date=datetime.now(UTC)); db.add(entry); db.flush()
    db.add_all([
        JournalLine(journal_entry_id=entry.id, account_id=bank.id, debit=Decimal("100000"), credit=Decimal("0")),
        JournalLine(journal_entry_id=entry.id, account_id=property_account.id, debit=Decimal("500000"), credit=Decimal("0")),
        JournalLine(journal_entry_id=entry.id, account_id=liability.id, debit=Decimal("0"), credit=Decimal("200000")),
        JournalLine(journal_entry_id=entry.id, account_id=credit_card.id, debit=Decimal("0"), credit=Decimal("10000")),
        JournalLine(journal_entry_id=entry.id, account_id=revenue.id, debit=Decimal("0"), credit=Decimal("100000")),
    ])
    db.add(Loan(name="Loan", lender="Bank", loan_type="LONG_TERM", principal_amount=Decimal("200000"), outstanding_balance=Decimal("200000"), amount_received=Decimal("200000"), fees=Decimal("0"), annual_rate=Decimal("5"), term_months=60, monthly_payment=Decimal("30000"), first_payment_date=date.today(), destination_account_code=1120, liability_account_code=2220, journal_entry_id=entry.id, status="ACTIVE"))
    db.add(CreditCardAccount(user_id=1, issuer_bank="Bank", card_name="Visa", last4="1234", credit_limit=Decimal("50000"), current_balance=Decimal("10000"), minimum_monthly_payment=Decimal("500"), currency_code="SAR"))
    db.add(BankAccount(user_id=1, bank_name="Bank", account_type="CURRENT", account_name="Primary", account_identifier="SA0001", current_balance=Decimal("100000"), currency_code="SAR"))
    db.commit()

    result = FinancialSummaryService(db, 1).get()
    assert result["total_assets"] == Decimal("600000.00")
    assert result["total_liabilities"] == Decimal("210000.00")
    assert result["net_worth"] == Decimal("390000.00")
    assert result["available_cash"] == Decimal("100000.00")
    assert result["dbr"] == Decimal("30.5")
    assert result["credit_card_summary"]["total_limit"] == Decimal("50000")
    assert result["credit_card_summary"]["used"] == Decimal("10000.00")
    assert result["credit_card_summary"]["available"] == Decimal("40000.00")
    assert result["risk_level"] == "MODERATE"


def test_opening_bank_balance_correction_is_not_cash_flow():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, JournalEntry.__table__, JournalLine.__table__, Loan.__table__, CreditCardAccount.__table__, BankAccount.__table__, Deposit.__table__, PropertyAsset.__table__])
    db = sessionmaker(bind=engine)()
    bank = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    equity = Account(code=3150, name="Opening Balance Equity", account_type="EQUITY", normal_balance="CREDIT")
    db.add_all([bank, equity]); db.flush()
    entry = JournalEntry(user_id=1, description="Opening balance correction", transaction_date=datetime.now(UTC), related_reference="opening-bank-account-adjustment:1:test")
    db.add(entry); db.flush()
    db.add_all([
        JournalLine(journal_entry_id=entry.id, account_id=bank.id, debit=Decimal("0.03"), credit=Decimal("0")),
        JournalLine(journal_entry_id=entry.id, account_id=equity.id, debit=Decimal("0"), credit=Decimal("0.03")),
    ])
    db.commit()

    result = FinancialSummaryService(db, 1).get()
    assert result["available_cash"] == Decimal("0.03")
    assert result["cash_inflow"] == Decimal("0.00")
    assert result["cash_outflow"] == Decimal("0.00")
    assert result["net_cash_flow"] == Decimal("0.00")


def test_non_cash_deposit_income_displays_the_recognized_income_amount():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, JournalEntry.__table__, JournalLine.__table__, Loan.__table__, CreditCardAccount.__table__, BankAccount.__table__, Deposit.__table__, PropertyAsset.__table__])
    db = sessionmaker(bind=engine)()
    deposit = Account(code=1160, name="Term Deposits", account_type="ASSET", normal_balance="DEBIT")
    income = Account(code=4400, name="Interest Income", account_type="REVENUE", normal_balance="CREDIT")
    db.add_all([deposit, income]); db.flush()
    product = Deposit(user_id=1, provider_name="Wadaie", product_name="Daily Yield Balance", product_type="INCOME_SAVINGS", principal_amount=Decimal("1000.00"), current_balance=Decimal("1002.84"), annual_return_rate=Decimal("4.00"), payout_frequency="DAILY", payout_schedule=[], start_date=date.today(), maturity_date=None, auto_renew=False, currency_code="SAR", status="ACTIVE")
    db.add(product); db.flush()
    entry = JournalEntry(user_id=1, description="Deposit income reconciliation · Daily Yield Balance", transaction_date=datetime.now(UTC), related_reference=f"deposit-return:{product.id}")
    db.add(entry); db.flush()
    db.add_all([
        JournalLine(journal_entry_id=entry.id, account_id=deposit.id, debit=Decimal("2.84"), credit=Decimal("0")),
        JournalLine(journal_entry_id=entry.id, account_id=income.id, debit=Decimal("0"), credit=Decimal("2.84")),
    ])
    db.commit()

    activity = FinancialSummaryService(db, 1).activity_for_month(entry.transaction_date.year, entry.transaction_date.month)
    assert activity[0]["cash_change"] == Decimal("0.00")
    assert activity[0]["display_amount"] == Decimal("2.84")
    assert activity[0]["return_status"] == "ACCRUED"

    product.status = "CLOSED"
    db.commit()
    activity = FinancialSummaryService(db, 1).activity_for_month(entry.transaction_date.year, entry.transaction_date.month)
    posted_return = next(item for item in activity if item["id"] == entry.id)
    assert posted_return["return_status"] == "REALIZED"


def test_card_to_card_payment_displays_the_transferred_amount():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, JournalEntry.__table__, JournalLine.__table__, Loan.__table__, CreditCardAccount.__table__, BankAccount.__table__, Deposit.__table__, PropertyAsset.__table__])
    db = sessionmaker(bind=engine)()
    cards = Account(code=2110, name="Credit Cards", account_type="LIABILITY", normal_balance="CREDIT")
    db.add(cards); db.flush()
    entry = JournalEntry(user_id=1, description="Credit Card Payment", transaction_date=datetime.now(UTC), related_reference="credit-card-sadad:2:12")
    db.add(entry); db.flush()
    db.add_all([
        JournalLine(journal_entry_id=entry.id, account_id=cards.id, debit=Decimal("10688.88"), credit=Decimal("0")),
        JournalLine(journal_entry_id=entry.id, account_id=cards.id, debit=Decimal("0"), credit=Decimal("10688.88")),
    ])
    db.commit()

    activity = FinancialSummaryService(db, 1).activity_for_month(entry.transaction_date.year, entry.transaction_date.month)
    posted = next(item for item in activity if item["id"] == entry.id)
    assert posted["cash_change"] == Decimal("0.00")
    assert posted["display_amount"] == Decimal("10688.88")


def test_historical_portfolio_movement_displays_amount_without_financial_effect():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, JournalEntry.__table__, JournalLine.__table__, Loan.__table__, CreditCardAccount.__table__, BankAccount.__table__, Deposit.__table__, PropertyAsset.__table__])
    db = sessionmaker(bind=engine)()
    memo = Account(code=3150, name="Opening Balance Equity", account_type="EQUITY", normal_balance="CREDIT")
    db.add(memo); db.flush()
    entry = JournalEntry(user_id=1, description="Historical money movement · Alinma Cashback · 140.00 SAR", transaction_date=datetime.now(UTC), related_reference="historical-portfolio-movement:9:bank-account:7")
    db.add(entry); db.flush()
    db.add_all([
        JournalLine(journal_entry_id=entry.id, account_id=memo.id, debit=Decimal("140.00"), credit=Decimal("0")),
        JournalLine(journal_entry_id=entry.id, account_id=memo.id, debit=Decimal("0"), credit=Decimal("140.00")),
    ]); db.commit()

    activity = FinancialSummaryService(db, 1).activity_for_month(entry.transaction_date.year, entry.transaction_date.month)
    posted = next(item for item in activity if item["id"] == entry.id)
    assert posted["cash_change"] == Decimal("0.00")
    assert posted["display_amount"] == Decimal("140.00")


def test_deposit_principal_return_is_not_counted_as_cash_income_flow():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, JournalEntry.__table__, JournalLine.__table__, Loan.__table__, CreditCardAccount.__table__, BankAccount.__table__, Deposit.__table__, PropertyAsset.__table__])
    db = sessionmaker(bind=engine)()
    bank = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    deposit = Account(code=1160, name="Term Deposits", account_type="ASSET", normal_balance="DEBIT")
    db.add_all([bank, deposit]); db.flush()
    entry = JournalEntry(user_id=1, description="Deposit withdrawal · Daily Deposit", transaction_date=datetime.now(UTC), related_reference="deposit-withdrawal:10")
    db.add(entry); db.flush()
    db.add_all([
        JournalLine(journal_entry_id=entry.id, account_id=bank.id, debit=Decimal("24036.26"), credit=Decimal("0")),
        JournalLine(journal_entry_id=entry.id, account_id=deposit.id, debit=Decimal("0"), credit=Decimal("24036.26")),
    ])
    db.commit()

    result = FinancialSummaryService(db, 1).get()
    assert result["cash_inflow"] == Decimal("0.00")
    assert result["cash_outflow"] == Decimal("0.00")
    assert result["net_cash_flow"] == Decimal("0.00")
