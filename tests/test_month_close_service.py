from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.accounting.models import Account, BankAccount
from app.accounting.schemas.journal import JournalLineInput
from app.accounting.services.ledger_service import LedgerService
from app.accounting.services.month_close_service import MonthCloseService
from app.accounting.services.reporting_service import ReportingService
from app.core.models.user import User
from app.database.base import Base


def previous_month() -> tuple[int, int]:
    today = date.today()
    return (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)


def test_monthly_snapshot_preserves_history_without_locking_personal_transactions():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id=1, email="close@example.com", full_name="Close Test")
    bank_ledger = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    income = Account(code=4100, name="Salary Income", account_type="REVENUE", normal_balance="CREDIT")
    db.add_all([user, bank_ledger, income]); db.flush()
    bank = BankAccount(user_id=1, bank_name="Bank", account_type="CURRENT", account_name="Primary", account_identifier="SA-CLOSE", current_balance=Decimal("150"), currency_code="SAR")
    db.add(bank); db.flush()
    year, month = previous_month(); period_start, _ = MonthCloseService.period(year, month)
    ledger = LedgerService(db)
    ledger.post("Opening balance · Primary", [JournalLineInput(account_id=bank_ledger.id, debit=Decimal("100"), credit=Decimal("0")), JournalLineInput(account_id=income.id, debit=Decimal("0"), credit=Decimal("100"))], user_id=1, transaction_date=datetime.combine(period_start, datetime.min.time()), related_reference=f"opening-bank-account:{bank.id}")
    ledger.post("Salary received", [JournalLineInput(account_id=bank_ledger.id, debit=Decimal("50"), credit=Decimal("0")), JournalLineInput(account_id=income.id, debit=Decimal("0"), credit=Decimal("50"))], user_id=1, transaction_date=datetime.combine(period_start, datetime.min.time()))
    db.commit()

    preview = MonthCloseService(db, 1).preview(year, month)
    assert preview["ready"] is True
    assert preview["reports"]["cash_flow_statement"]["rows"][-1]["value"] == 50
    closed = MonthCloseService(db, 1).close(year, month)
    assert closed.status == "CLOSED"
    assert len(closed.checksum) == 64
    original_checksum = closed.checksum
    live_report = ReportingService(db, 1).get("cash_flow_statement", closed.period_start, closed.period_end)
    assert live_report["basis"] == "Posted journal entries"
    ledger.post("Late income", [JournalLineInput(account_id=bank_ledger.id, debit=Decimal("1"), credit=Decimal("0")), JournalLineInput(account_id=income.id, debit=Decimal("0"), credit=Decimal("1"))], user_id=1, transaction_date=datetime.combine(period_start, datetime.min.time()))
    bank.current_balance = Decimal("151")
    db.commit()
    refreshed = MonthCloseService(db, 1).close(year, month)
    assert refreshed.id != closed.id
    assert refreshed.version == 2
    assert refreshed.predecessor_id == closed.id
    assert refreshed.checksum != original_checksum
    db.refresh(closed)
    assert closed.checksum == original_checksum


def test_monthly_snapshot_can_be_saved_even_when_later_periods_have_activity():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id=1, email="sequence@example.com", full_name="Sequence Test")
    bank_ledger = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    income = Account(code=4100, name="Salary Income", account_type="REVENUE", normal_balance="CREDIT")
    db.add_all([user, bank_ledger, income]); db.flush()
    year, month = previous_month(); period_start, period_end = MonthCloseService.period(year, month)
    bank = BankAccount(user_id=1, bank_name="Bank", account_type="CURRENT", account_name="Primary", account_identifier="SA-SEQUENCE", current_balance=Decimal("100"), currency_code="SAR")
    db.add(bank); db.flush()
    ledger = LedgerService(db)
    lines = [JournalLineInput(account_id=bank_ledger.id, debit=Decimal("100"), credit=Decimal("0")), JournalLineInput(account_id=income.id, debit=Decimal("0"), credit=Decimal("100"))]
    ledger.post("Opening balance · Primary", lines, user_id=1, transaction_date=datetime.combine(period_start, datetime.min.time()), related_reference=f"opening-bank-account:{bank.id}")
    ledger.post("Later month entry", [JournalLineInput(account_id=bank_ledger.id, debit=Decimal("1"), credit=Decimal("0")), JournalLineInput(account_id=income.id, debit=Decimal("0"), credit=Decimal("1"))], user_id=1, transaction_date=datetime.combine(period_end + timedelta(days=1), datetime.min.time()))
    db.commit()

    preview = MonthCloseService(db, 1).preview(year, month)
    assert preview["later_entries_count"] == 1
    assert preview["ready"] is True
    snapshot = MonthCloseService(db, 1).close(year, month)
    assert snapshot.status == "CLOSED"


def test_monthly_snapshot_requires_readiness_and_preserves_deterministic_versions():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id=1, email="versions@example.com", full_name="Version Test")
    bank_ledger = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    equity = Account(code=3100, name="Opening Equity", account_type="EQUITY", normal_balance="CREDIT")
    db.add_all([user, bank_ledger, equity]); db.flush()
    year, month = previous_month(); period_start, _ = MonthCloseService.period(year, month)
    bank = BankAccount(user_id=1, bank_name="Bank", account_type="CURRENT", account_name="Primary", account_identifier="SA-VERSION", current_balance=Decimal("99"), currency_code="SAR")
    db.add(bank)
    LedgerService(db).post("Opening balance · Primary", [JournalLineInput(bank_ledger.id, Decimal("100"), Decimal("0")), JournalLineInput(equity.id, Decimal("0"), Decimal("100"))], user_id=1, transaction_date=datetime.combine(period_start, datetime.min.time()), related_reference=f"opening-bank-account:{bank.id}")
    db.commit()

    service = MonthCloseService(db, 1)
    assert service.preview(year, month)["ready"] is False
    with pytest.raises(ValueError, match="mandatory accounting checks"):
        service.close(year, month)

    bank.current_balance = Decimal("100")
    db.commit()
    first = service.close(year, month)
    second = service.close(year, month)
    assert first.id != second.id
    assert (first.version, second.version) == (1, 2)
    assert second.predecessor_id == first.id
    assert first.checksum == second.checksum
    assert db.query(type(first)).filter_by(user_id=1, period_end=first.period_end).count() == 2
