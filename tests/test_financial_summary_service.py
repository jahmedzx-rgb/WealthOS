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
