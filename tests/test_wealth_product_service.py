from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.accounting.models import Account, AlternativeInvestment, BankAccount, JournalEntry, JournalLine, SavingCircle
from app.accounting.schemas.wealth_products import AlternativeInvestmentRequest, SavingCircleRequest
from app.accounting.services.financial_summary_service import FinancialSummaryService
from app.accounting.services.wealth_product_service import WealthProductService
from app.core.models.user import User
from app.database.base import Base


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(User(id=1, email="wealth@example.com", full_name="Wealth User"))
    db.add_all([
        Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=1170, name="Saving Circles", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=1380, name="Crowdfunding Investments", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=1390, name="Other Investments", account_type="ASSET", normal_balance="DEBIT"),
    ])
    db.add(BankAccount(id=1, user_id=1, bank_name="Bank", account_type="CURRENT", account_name="Primary", account_identifier="SA001", current_balance=Decimal("10000"), currency_code="SAR"))
    opening = JournalEntry(user_id=1, description="Opening bank", transaction_date=datetime(2026, 1, 1, tzinfo=UTC), related_reference="bank-account:1")
    db.add(opening); db.flush()
    db.add(JournalLine(journal_entry_id=opening.id, account_id=db.query(Account).filter_by(code=1120).one().id, debit=Decimal("10000"), credit=0))
    db.commit()
    return db


def test_saving_circle_is_receivable_not_available_cash():
    db = make_db()
    item = WealthProductService(db, 1).create_saving_circle(SavingCircleRequest(platform_name="Hakbah", circle_name="Family Circle", installment_amount=Decimal("500"), frequency="MONTHLY", total_installments=10, payout_installment=8, installments_paid=2, start_date=date(2026, 1, 1), funding_bank_account_id=1, transaction_date=datetime(2026, 2, 1, tzinfo=UTC)))
    summary = FinancialSummaryService(db, 1).get()
    assert item.installments_paid == 2
    assert db.get(BankAccount, 1).current_balance == Decimal("9000")
    assert summary["available_cash"] == Decimal("9000")
    assert next(row for row in summary["asset_breakdown"] if row["code"] == 1170)["balance"] == Decimal("1000")


def test_alternative_investment_posts_to_crowdfunding_ledger():
    db = make_db()
    item = WealthProductService(db, 1).create_alternative(AlternativeInvestmentRequest(platform_name="Tarmeez Capital", investment_name="Private Sukuk 01", investment_type="DEBT_CROWDFUNDING", funding_bank_account_id=1, principal_amount=Decimal("2500"), expected_annual_return=Decimal("8"), investment_date=date(2026, 2, 1), maturity_date=date(2027, 2, 1), distribution_frequency="AT_MATURITY", currency_code="SAR", transaction_date=datetime(2026, 2, 1, tzinfo=UTC)))
    lines = db.query(JournalLine).join(Account).filter(Account.code == 1380).all()
    assert item.current_value == Decimal("2500")
    assert db.get(BankAccount, 1).current_balance == Decimal("7500")
    assert sum(line.debit for line in lines) == Decimal("2500")
