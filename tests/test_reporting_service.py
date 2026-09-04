from datetime import UTC, date, datetime
from decimal import Decimal
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.accounting.models.account import Account
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.services.reporting_service import ReportingService
from app.api.v1.accounting import periodic_financial_reports
from app.database.base import Base


def test_income_detail_reports_only_include_the_requested_posted_category():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, JournalEntry.__table__, JournalLine.__table__])
    db = sessionmaker(bind=engine)()
    bank = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    rental = Account(code=4200, name="Rental Income", account_type="REVENUE", normal_balance="CREDIT")
    dividend = Account(code=4300, name="Dividend Income", account_type="REVENUE", normal_balance="CREDIT")
    interest = Account(code=4400, name="Interest Income", account_type="REVENUE", normal_balance="CREDIT")
    db.add_all([bank, rental, dividend, interest]); db.flush()
    for description, account, amount in [("August rent · Villa", rental, "17000"), ("Fund distribution · 4348", dividend, "250"), ("Deposit return · Wadaie", interest, "80")]:
        entry = JournalEntry(user_id=1, description=description, transaction_date=datetime(2026, 8, 20)); db.add(entry); db.flush()
        db.add_all([JournalLine(journal_entry_id=entry.id, account_id=bank.id, debit=Decimal(amount), credit=0), JournalLine(journal_entry_id=entry.id, account_id=account.id, debit=0, credit=Decimal(amount))])
    db.commit()

    result = ReportingService(db, 1).get("property_income", date(2026, 8, 1), date(2026, 8, 31))
    assert result["source_entry_count"] == 1
    assert result["rows"][0]["label"] == "August rent · Villa"
    assert result["rows"][-1]["value"] == Decimal("17000")

    result = ReportingService(db, 1).get("distribution_income", date(2026, 8, 1), date(2026, 8, 31))
    assert result["rows"][-1]["value"] == Decimal("250")

    result = ReportingService(db, 1).get("deposit_income", date(2026, 8, 1), date(2026, 8, 31))
    assert result["rows"][-1]["value"] == Decimal("80")


def test_cash_flow_statement_links_investment_income_and_asset_movements():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, JournalEntry.__table__, JournalLine.__table__])
    db = sessionmaker(bind=engine)()
    bank = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    rental = Account(code=4200, name="Rental Income", account_type="REVENUE", normal_balance="CREDIT")
    property_asset = Account(code=1210, name="Real Estate", account_type="ASSET", normal_balance="DEBIT")
    loan = Account(code=2220, name="Loan", account_type="LIABILITY", normal_balance="CREDIT")
    db.add_all([bank, rental, property_asset, loan]); db.flush()

    movements = [
        ("Rent received · Villa", rental, Decimal("17000"), True),
        ("Property purchase · Villa", property_asset, Decimal("700000"), False),
        ("Loan proceeds", loan, Decimal("100000"), True),
    ]
    for description, counterpart, amount, cash_in in movements:
        entry = JournalEntry(user_id=1, description=description, transaction_date=datetime(2026, 8, 20)); db.add(entry); db.flush()
        db.add_all([
            JournalLine(journal_entry_id=entry.id, account_id=bank.id, debit=amount if cash_in else 0, credit=0 if cash_in else amount),
            JournalLine(journal_entry_id=entry.id, account_id=counterpart.id, debit=0 if cash_in else amount, credit=amount if cash_in else 0),
        ])
    db.commit()

    result = ReportingService(db, 1).get("cash_flow_statement", date(2026, 8, 1), date(2026, 8, 31))
    details = {row["label"]: row for row in result["rows"] if not row["is_total"]}
    assert details["Rent received · Villa"]["section"].startswith("Operating")
    assert details["Rent received · Villa"]["value"] == Decimal("17000")
    assert details["Property purchase · Villa"]["section"].startswith("Investing")
    assert details["Property purchase · Villa"]["value"] == Decimal("-700000")
    assert details["Loan proceeds"]["section"].startswith("Financing")
    totals = {row["label"]: row["value"] for row in result["rows"] if row["is_total"]}
    assert totals["Net Cash From Operating Activities"] == Decimal("17000")
    assert totals["Net Cash From Investing Activities"] == Decimal("-700000")
    assert totals["Net Cash From Financing Activities"] == Decimal("100000")
    assert totals["Net Change In Cash"] == Decimal("-583000")


def test_riyadh_month_boundary_includes_each_posting_exactly_once():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, JournalEntry.__table__, JournalLine.__table__])
    db = sessionmaker(bind=engine)()
    bank = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    income = Account(code=4100, name="Income", account_type="REVENUE", normal_balance="CREDIT")
    db.add_all([bank, income]); db.flush()
    for instant, amount in [(datetime(2026, 8, 31, 20, 59, 59, tzinfo=UTC), "10"), (datetime(2026, 8, 31, 21, 0, 0, tzinfo=UTC), "20")]:
        entry = JournalEntry(user_id=1, description=f"Boundary {amount}", transaction_date=instant)
        db.add(entry); db.flush()
        db.add_all([JournalLine(journal_entry_id=entry.id, account_id=bank.id, debit=Decimal(amount), credit=0), JournalLine(journal_entry_id=entry.id, account_id=income.id, debit=0, credit=Decimal(amount))])
    db.commit()

    august = ReportingService(db, 1).get("income_statement", date(2026, 8, 1), date(2026, 8, 31))
    september = ReportingService(db, 1).get("income_statement", date(2026, 9, 1), date(2026, 9, 30))
    assert august["rows"][-1]["value"] == Decimal("10")
    assert september["rows"][-1]["value"] == Decimal("20")


def test_monthly_periodic_api_caps_the_display_window_at_four_months():
    with pytest.raises(HTTPException) as exc:
        periodic_financial_reports("balance_sheet", "MONTHLY", 5, date(2026, 8, 31), None, None)
    assert exc.value.status_code == 422
    assert "between 2 and 4" in exc.value.detail
