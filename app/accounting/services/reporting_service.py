from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.models.account import Account
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.services.accounting_period import period_utc_bounds


class ReportingService:
    CASH_ACCOUNT_NAMES = {
        "Cash", "Cash on Hand", "Bank Accounts", "Primary Bank Account",
        "Brokerage Cash", "Digital Wallets", "Foreign Currency Cash",
    }

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def get(self, report_type: str, start_date: date, end_date: date) -> dict:
        if start_date > end_date:
            raise ValueError("يجب أن يكون تاريخ البداية في تاريخ النهاية أو قبله.")
        period_start_at, period_end_at = period_utc_bounds(start_date, end_date)
        query = (
            self.db.query(JournalLine, Account, JournalEntry)
            .join(Account, JournalLine.account_id == Account.id)
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .filter(JournalEntry.user_id == self.user_id, JournalEntry.transaction_date < period_end_at)
        )
        all_rows = query.all()
        period_rows = query.filter(JournalEntry.transaction_date >= period_start_at).all()
        rows: list[dict] = []
        source_entry_ids: set[int] = set()

        income_detail_codes = {
            "property_income": (4200, "Total Property Income"),
            "deposit_income": (4400, "Total Deposit & Interest Income"),
            "distribution_income": (4300, "Total Investment Distributions"),
        }
        if report_type in income_detail_codes:
            account_code, total_label = income_detail_codes[report_type]
            total = Decimal("0")
            for line, account, entry in sorted(period_rows, key=lambda item: (item[2].transaction_date, item[2].id)):
                if account.code != account_code:
                    continue
                value = (line.credit or 0) - (line.debit or 0)
                if value == 0:
                    continue
                total += value
                source_entry_ids.add(entry.id)
                rows.append({
                    "code": account.code,
                    "label": entry.description,
                    "section": entry.transaction_date.date().isoformat(),
                    "value": value,
                    "is_total": False,
                })
            rows.append(self._total(total_label, total))
        elif report_type == "income_statement":
            grouped = self._account_balances(period_rows, {"REVENUE", "EXPENSE"}, source_entry_ids)
            income_total = Decimal("0")
            expense_total = Decimal("0")
            for account, balance in grouped:
                if account.account_type == "REVENUE":
                    income_total += balance
                    rows.append(self._row(account, balance, "Income"))
            rows.append(self._total("Total Income", income_total))
            for account, balance in grouped:
                if account.account_type == "EXPENSE":
                    expense_total += balance
                    rows.append(self._row(account, -balance, "Expense"))
            rows.extend([self._total("Total Expenses", -expense_total), self._total("Net Surplus", income_total - expense_total)])
        elif report_type in {"balance_sheet", "net_worth"}:
            grouped = self._account_balances(all_rows, {"ASSET", "LIABILITY"}, source_entry_ids)
            assets = Decimal("0")
            liabilities = Decimal("0")
            for account, balance in grouped:
                if account.account_type == "ASSET" and balance != 0:
                    assets += balance
                    rows.append(self._row(account, balance, "Asset"))
            rows.append(self._total("Total Assets", assets))
            for account, balance in grouped:
                if account.account_type == "LIABILITY" and balance != 0:
                    liabilities += balance
                    rows.append(self._row(account, balance, "Liability"))
            rows.extend([self._total("Total Liabilities", liabilities), self._total("Net Worth", assets - liabilities)])
        elif report_type == "cash_flow_statement":
            entry_changes: dict[int, Decimal] = {}
            entry_rows: dict[int, list[tuple[JournalLine, Account, JournalEntry]]] = {}
            for line, account, entry in period_rows:
                entry_rows.setdefault(entry.id, []).append((line, account, entry))
                if account.account_type != "ASSET" or account.name not in self.CASH_ACCOUNT_NAMES:
                    continue
                legacy_bank_opening = entry.related_reference.startswith("bank-account:") and entry.description.startswith("Opening balance ·") if entry.related_reference else False
                if entry.related_reference and entry.related_reference.startswith(("opening-bank-account:", "opening-cash", "opening-inheritance:")) or legacy_bank_opening:
                    continue
                entry_changes[entry.id] = entry_changes.get(entry.id, Decimal("0")) + (line.debit or 0) - (line.credit or 0)
            sections = {"Operating": Decimal("0"), "Investing": Decimal("0"), "Financing": Decimal("0")}
            detail_rows: list[dict] = []
            for entry_id, value in sorted(entry_changes.items(), key=lambda item: (entry_rows[item[0]][0][2].transaction_date, item[0])):
                if value == 0:
                    continue
                entry = entry_rows[entry_id][0][2]
                section = self._cash_flow_section(entry_rows[entry_id])
                sections[section] += value
                source_entry_ids.add(entry_id)
                detail_rows.append({
                    "code": None,
                    "label": entry.description,
                    "section": f"{section} · {entry.transaction_date.date().isoformat()}",
                    "value": value,
                    "is_total": False,
                })
            rows = detail_rows
            rows.extend([
                self._section_total("Net Cash From Operating Activities", sections["Operating"], "Operating"),
                self._section_total("Net Cash From Investing Activities", sections["Investing"], "Investing"),
                self._section_total("Net Cash From Financing Activities", sections["Financing"], "Financing"),
                self._total("Net Change In Cash", sum(sections.values(), Decimal("0"))),
            ])
        else:
            raise ValueError("نوع التقرير غير مدعوم.")

        return {
            "report_type": report_type,
            "start_date": start_date,
            "end_date": end_date,
            "basis": "Posted journal entries",
            "source_entry_count": len(source_entry_ids),
            "generated_at": datetime.now(UTC),
            "rows": rows,
        }

    def _account_balances(self, source_rows, account_types: set[str], source_entry_ids: set[int]):
        balances: dict[int, Decimal] = {}
        accounts: dict[int, Account] = {}
        for line, account, entry in source_rows:
            if account.account_type not in account_types:
                continue
            movement = (line.debit or 0) - (line.credit or 0)
            if account.account_type in {"LIABILITY", "REVENUE"}:
                movement = -movement
            balances[account.id] = balances.get(account.id, Decimal("0")) + movement
            accounts[account.id] = account
            source_entry_ids.add(entry.id)
        return sorted(((accounts[key], value) for key, value in balances.items() if value != 0), key=lambda item: item[0].code)

    @staticmethod
    def _row(account: Account, value: Decimal, section: str) -> dict:
        return {"code": account.code, "label": account.name, "section": section, "value": value, "is_total": False}

    @staticmethod
    def _total(label: str, value: Decimal) -> dict:
        return {"code": None, "label": label, "section": "Total", "value": value, "is_total": True}

    @staticmethod
    def _section_total(label: str, value: Decimal, section: str) -> dict:
        return {"code": None, "label": label, "section": section, "value": value, "is_total": True}

    @staticmethod
    def _cash_flow_section(rows: list[tuple[JournalLine, Account, JournalEntry]]) -> str:
        non_cash_accounts = [account for _, account, _ in rows if account.name not in ReportingService.CASH_ACCOUNT_NAMES]
        if any(account.account_type == "ASSET" and (account.code in {1160, 1170} or 1200 <= account.code < 1400) for account in non_cash_accounts):
            return "Investing"
        if any(account.account_type in {"LIABILITY", "EQUITY"} for account in non_cash_accounts):
            return "Financing"
        return "Operating"
