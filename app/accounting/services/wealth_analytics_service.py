from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.models.account import Account
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.models.wealth_analytics_snapshot import WealthAnalyticsSnapshot
from app.accounting.services.financial_summary_service import FinancialSummaryService


ZERO = Decimal("0.00")
TRANSFER_PREFIXES = (
    "account-transfer:", "credit-card-sadad:", "credit-card-payment:",
    "portfolio-funding:", "portfolio-withdrawal:", "deposit-withdrawal:",
    "historical-portfolio-movement:",
)
OPENING_PREFIXES = (
    "opening-", "bank-account-created:", "credit-card-created:",
    "deposit-created:", "portfolio-created:",
)


def classify_journal_entry(reference: str | None, lines: list[tuple[Account, JournalLine]]) -> dict:
    """Classify a balanced entry without treating money moved internally as new income."""
    ref = reference or ""
    debit_total = sum((line.debit or ZERO for _, line in lines), ZERO)
    amount = debit_total
    revenue = sum(((line.credit or ZERO) - (line.debit or ZERO) for account, line in lines if account.account_type == "REVENUE"), ZERO)
    expense = sum(((line.debit or ZERO) - (line.credit or ZERO) for account, line in lines if account.account_type == "EXPENSE"), ZERO)
    equity = sum(((line.credit or ZERO) - (line.debit or ZERO) for account, line in lines if account.account_type == "EQUITY"), ZERO)
    has_investment_asset_debit = any(account.account_type == "ASSET" and account.code not in {1110, 1120, 1130, 1140, 1150} and (line.debit or ZERO) > 0 for account, line in lines)

    if ref.startswith(OPENING_PREFIXES) or (ref.startswith("bank-account:") and "opening" in ref.lower()):
        return {"kind": "OPENING_BALANCE", "amount": amount, "income": ZERO, "expense": ZERO, "destination": "OPENING_BALANCE"}
    if ref.startswith(TRANSFER_PREFIXES) or (revenue == 0 and expense == 0 and equity == 0):
        return {"kind": "INTERNAL_TRANSFER", "amount": amount, "income": ZERO, "expense": ZERO, "destination": "TRANSFERRED"}
    if "principal-return" in ref:
        return {"kind": "PRINCIPAL_RETURN", "amount": amount, "income": ZERO, "expense": ZERO, "destination": "CASH_RETAINED"}
    if revenue > 0:
        return {"kind": "INVESTMENT_INCOME", "amount": revenue, "income": revenue, "expense": ZERO, "destination": "REINVESTED" if has_investment_asset_debit else "CASH_RETAINED"}
    if expense > 0:
        return {"kind": "EXPENSE", "amount": expense, "income": ZERO, "expense": expense, "destination": "SPENT"}
    if equity > 0:
        return {"kind": "OWNER_FUNDING", "amount": equity, "income": ZERO, "expense": ZERO, "destination": "FUNDED_ASSETS"}
    return {"kind": "UNCLASSIFIED", "amount": amount, "income": ZERO, "expense": ZERO, "destination": "UNCLASSIFIED"}


class WealthAnalyticsService:
    PERIOD_DAYS = {"1W": 7, "1M": 30, "1Y": 365}

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def _start(self, period: str, today: date) -> date:
        if period == "YTD":
            return date(today.year, 1, 1)
        if period not in self.PERIOD_DAYS:
            raise ValueError("Period must be 1W, 1M, YTD, or 1Y.")
        return today - timedelta(days=self.PERIOD_DAYS[period] - 1)

    def _capture_snapshot(self, summary: dict, today: date) -> WealthAnalyticsSnapshot:
        row = self.db.query(WealthAnalyticsSnapshot).filter_by(user_id=self.user_id, snapshot_date=today).one_or_none()
        if row is None:
            row = WealthAnalyticsSnapshot(user_id=self.user_id, snapshot_date=today)
            self.db.add(row)
        row.total_assets = summary["total_assets"]
        row.total_liabilities = summary["total_liabilities"]
        row.net_worth = summary["net_worth"]
        row.available_cash = summary["available_cash"]
        row.recorded_at = datetime.now(UTC)
        self.db.commit()
        return row

    def get(self, period: str) -> dict:
        today = datetime.now(UTC).date()
        start = self._start(period, today)
        summary = FinancialSummaryService(self.db, self.user_id).get()
        self._capture_snapshot(summary, today)
        rows = (self.db.query(JournalEntry, JournalLine, Account)
            .join(JournalLine, JournalLine.journal_entry_id == JournalEntry.id)
            .join(Account, Account.id == JournalLine.account_id)
            .filter(JournalEntry.user_id == self.user_id, JournalEntry.transaction_date >= datetime.combine(start, datetime.min.time()))
            .order_by(JournalEntry.transaction_date, JournalEntry.id).all())
        grouped: dict[int, dict] = {}
        for entry, line, account in rows:
            grouped.setdefault(entry.id, {"entry": entry, "lines": []})["lines"].append((account, line))

        kinds = defaultdict(lambda: ZERO)
        destinations = defaultdict(lambda: ZERO)
        income_by_account = defaultdict(lambda: ZERO)
        transfer_excluded = ZERO
        classified = 0
        for group in grouped.values():
            result = classify_journal_entry(group["entry"].related_reference, group["lines"])
            kinds[result["kind"]] += result["amount"]
            destinations[result["destination"]] += result["amount"]
            classified += result["kind"] != "UNCLASSIFIED"
            if result["kind"] == "INTERNAL_TRANSFER":
                transfer_excluded += result["amount"]
            for account, line in group["lines"]:
                if account.account_type == "REVENUE":
                    income_by_account[account.name] += (line.credit or ZERO) - (line.debit or ZERO)

        snapshots = self.db.query(WealthAnalyticsSnapshot).filter(
            WealthAnalyticsSnapshot.user_id == self.user_id,
            WealthAnalyticsSnapshot.snapshot_date >= start,
        ).order_by(WealthAnalyticsSnapshot.snapshot_date).all()
        return {
            "period": period, "start_date": start, "end_date": today,
            "growth_sources": {
                "owner_funding": kinds["OWNER_FUNDING"],
                "investment_income": kinds["INVESTMENT_INCOME"],
                "expenses": kinds["EXPENSE"],
            },
            "destinations": {
                "cash_retained": destinations["CASH_RETAINED"],
                "reinvested": destinations["REINVESTED"],
                "spent": destinations["SPENT"],
                "funded_assets": destinations["FUNDED_ASSETS"],
            },
            "top_income": [{"label": name, "value": value} for name, value in sorted(income_by_account.items(), key=lambda item: item[1], reverse=True) if value > 0],
            "transfer_excluded_total": transfer_excluded,
            "classification_coverage": Decimal(classified) / Decimal(len(grouped)) * 100 if grouped else Decimal("100"),
            "snapshots": [{"date": row.snapshot_date, "net_worth": row.net_worth, "total_assets": row.total_assets, "available_cash": row.available_cash} for row in snapshots],
        }
