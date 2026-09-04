import hashlib
import json
from calendar import monthrange
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.accounting.models import Account, BankAccount, Deposit, JournalEntry, JournalLine, PropertyAsset
from app.accounting.models.month_close import MonthClose
from app.accounting.services.accounting_period import period_utc_bounds
from app.accounting.services.reporting_service import ReportingService
from app.investing.models.portfolio import Portfolio


class MonthCloseService:
    TOLERANCE = Decimal("0.01")
    COMPARISON_CODES = {
        "Bank accounts": 1120,
        "Brokerage cash": 1130,
        "Active deposits": 1160,
        "Active properties": 1210,
    }

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    @staticmethod
    def period(year: int, month: int) -> tuple[date, date]:
        return date(year, month, 1), date(year, month, monthrange(year, month)[1])

    def _ledger_balance(self, code: int, period_end: date) -> Decimal:
        _, period_end_at = period_utc_bounds(period_end, period_end)
        return self.db.query(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0)).join(JournalEntry).join(Account, Account.id == JournalLine.account_id).filter(JournalEntry.user_id == self.user_id, JournalEntry.transaction_date < period_end_at, Account.code == code).scalar() or Decimal("0")

    def _latest(self, period_end: date) -> MonthClose | None:
        return self.db.query(MonthClose).filter(MonthClose.user_id == self.user_id, MonthClose.period_end == period_end).order_by(MonthClose.version.desc()).first()

    def _current_operational_values(self) -> dict[str, Decimal]:
        return {
            "Bank accounts": sum((item.current_balance for item in self.db.query(BankAccount).filter(BankAccount.user_id == self.user_id).all()), Decimal("0")),
            "Brokerage cash": sum((item.cash_balance for item in self.db.query(Portfolio).join(Portfolio.entity).filter_by(user_id=self.user_id).all()), Decimal("0")),
            "Active deposits": sum((item.current_balance for item in self.db.query(Deposit).filter(Deposit.user_id == self.user_id, Deposit.status == "ACTIVE").all()), Decimal("0")),
            "Active properties": sum((item.current_value for item in self.db.query(PropertyAsset).filter(PropertyAsset.user_id == self.user_id, PropertyAsset.status == "ACTIVE").all()), Decimal("0")),
        }

    def _operational_values_as_of(self, period_end: date, previous: MonthClose | None) -> tuple[dict[str, Decimal], str]:
        if previous is None:
            return self._current_operational_values(), "CURRENT_OPERATIONAL_RECORDS"
        prior = {item["label"]: Decimal(str(item["operational"])) for item in previous.checklist.get("comparisons", [])}
        _, period_end_at = period_utc_bounds(period_end, period_end)
        for label, code in self.COMPARISON_CODES.items():
            delta = self.db.query(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0)).join(JournalEntry).join(Account, Account.id == JournalLine.account_id).filter(
                JournalEntry.user_id == self.user_id,
                JournalEntry.transaction_date < period_end_at,
                JournalEntry.created_at > previous.closed_at,
                Account.code == code,
            ).scalar() or Decimal("0")
            prior[label] = prior.get(label, Decimal("0")) + delta
        return prior, f"SNAPSHOT_V{previous.version}_PLUS_LATE_POSTINGS"

    def preview(self, year: int, month: int) -> dict:
        period_start, period_end = self.period(year, month)
        _, period_end_at = period_utc_bounds(period_end, period_end)
        grouped = self.db.query(JournalEntry.id, JournalEntry.description, func.sum(JournalLine.debit), func.sum(JournalLine.credit)).join(JournalLine).filter(JournalEntry.user_id == self.user_id, JournalEntry.transaction_date < period_end_at).group_by(JournalEntry.id).all()
        unbalanced = [{"entry_id": entry_id, "description": description, "debit": debit, "credit": credit} for entry_id, description, debit, credit in grouped if debit != credit]
        later_entries_count = self.db.query(JournalEntry.id).filter(JournalEntry.user_id == self.user_id, JournalEntry.transaction_date >= period_end_at).count()
        existing = self._latest(period_end)
        operational, comparison_basis = self._operational_values_as_of(period_end, existing)
        comparisons = [self._comparison(label, self._ledger_balance(code, period_end), operational.get(label, Decimal("0")), comparison_basis) for label, code in self.COMPARISON_CODES.items()]
        reports = {key: ReportingService(self.db, self.user_id).get(key, period_start, period_end) for key in ("income_statement", "cash_flow_statement", "balance_sheet")}
        ready = not unbalanced and all(item["matches"] for item in comparisons)
        return jsonable_encoder({"period_start": period_start, "period_end": period_end, "ready": ready, "later_entries_count": later_entries_count, "unbalanced_entries": unbalanced, "comparisons": comparisons, "reports": reports, "existing_close": self._dict(existing) if existing else None})

    def close(self, year: int, month: int) -> MonthClose:
        period_start, period_end = self.period(year, month)
        preview = self.preview(year, month)
        if not preview["ready"]:
            raise ValueError("لا يمكن حفظ اللقطة الشهرية حتى تنجح جميع الفحوص المحاسبية الإلزامية.")
        snapshot = preview["reports"]
        checksum = self._checksum(snapshot)
        previous = self._latest(period_end)
        item = MonthClose(
            user_id=self.user_id,
            period_start=period_start,
            period_end=period_end,
            version=(previous.version + 1) if previous else 1,
            predecessor_id=previous.id if previous else None,
            snapshot=snapshot,
            checklist={"comparison_basis": preview["comparisons"][0]["basis"] if preview["comparisons"] else None, "comparisons": preview["comparisons"], "unbalanced_entries": preview["unbalanced_entries"]},
            checksum=checksum,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def reopen(self, close_id: int, reason: str) -> MonthClose:
        item = self.db.query(MonthClose).filter(MonthClose.id == close_id, MonthClose.user_id == self.user_id).first()
        if item is None:
            raise ValueError("لم يتم العثور على الإقفال الشهري.")
        if item.status != "CLOSED":
            raise ValueError("هذا الشهر مفتوح بالفعل.")
        item.status = "REOPENED"
        item.reopened_at = datetime.now(UTC)
        item.reopen_reason = reason.strip()
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(self) -> list[MonthClose]:
        return self.db.query(MonthClose).filter(MonthClose.user_id == self.user_id).order_by(MonthClose.period_end.desc(), MonthClose.version.desc()).all()

    def _comparison(self, label: str, ledger: Decimal, operational: Decimal, basis: str) -> dict:
        variance = ledger - operational
        return {"label": label, "ledger": ledger, "operational": operational, "variance": variance, "matches": abs(variance) <= self.TOLERANCE, "basis": basis}

    @classmethod
    def _checksum(cls, snapshot: dict) -> str:
        canonical = cls._canonical(snapshot)
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def _canonical(cls, value):
        if isinstance(value, dict):
            return {key: cls._canonical(item) for key, item in value.items() if key != "generated_at"}
        if isinstance(value, list):
            return [cls._canonical(item) for item in value]
        return value

    @staticmethod
    def _dict(item: MonthClose) -> dict:
        return {column.name: getattr(item, column.name) for column in item.__table__.columns}
