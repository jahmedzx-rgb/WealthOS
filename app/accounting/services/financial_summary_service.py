from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.accounting.models.account import Account
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.models.loan import Loan
from app.accounting.models.credit_card_account import CreditCardAccount
from app.accounting.models.bank_account import BankAccount
from app.accounting.bank_identifiers import mask_bank_account_identifier
from app.accounting.models.deposit import Deposit
from app.accounting.models.property_asset import PropertyAsset
from app.accounting.models.month_close import MonthClose


class FinancialSummaryService:
    CASH_ACCOUNT_NAMES = {"Cash", "Cash on Hand", "Bank Accounts", "Primary Bank Account", "Brokerage Cash", "Digital Wallets", "Foreign Currency Cash"}

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def get(self) -> dict:
        rows = (
            self.db.query(JournalLine, Account, JournalEntry)
            .join(Account, JournalLine.account_id == Account.id)
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .filter(JournalEntry.user_id == self.user_id)
            .all()
        )
        now = datetime.now(UTC)
        current_close = latest_close = None
        if inspect(self.db.connection()).has_table("month_closes"):
            current_close = self.db.query(MonthClose).filter(
                MonthClose.user_id == self.user_id,
                MonthClose.period_start <= now.date(),
                MonthClose.period_end >= now.date(),
                MonthClose.status == "CLOSED",
            ).first()
            latest_close = self.db.query(MonthClose).filter(MonthClose.user_id == self.user_id, MonthClose.status == "CLOSED").order_by(MonthClose.period_end.desc()).first()
        balances: dict[int, Decimal] = {}
        accounts: dict[int, Account] = {}
        available_cash = Decimal("0.00")
        monthly_income = Decimal("0.00")
        monthly_expenses = Decimal("0.00")
        income_by_account: dict[int, Decimal] = {}
        expense_by_account: dict[int, Decimal] = {}
        entry_cash_changes: dict[int, Decimal] = {}
        entry_bank_changes: dict[int, Decimal] = {}
        rental_income_ttm = Decimal("0.00")

        for line, account, entry in rows:
            debit = line.debit or Decimal("0.00")
            credit = line.credit or Decimal("0.00")
            accounts[account.id] = account
            if account.account_type == "ASSET":
                balance = debit - credit
                balances[account.id] = balances.get(account.id, Decimal("0.00")) + balance
                if account.name in self.CASH_ACCOUNT_NAMES:
                    available_cash += balance
                    entry_cash_changes[entry.id] = entry_cash_changes.get(entry.id, Decimal("0.00")) + balance
                if account.code == 1120:
                    entry_bank_changes[entry.id] = entry_bank_changes.get(entry.id, Decimal("0.00")) + balance
            elif account.account_type == "LIABILITY":
                balances[account.id] = balances.get(account.id, Decimal("0.00")) + credit - debit
            elif account.account_type == "REVENUE" and entry.transaction_date.year == now.year and entry.transaction_date.month == now.month:
                movement = credit - debit
                monthly_income += movement
                income_by_account[account.id] = income_by_account.get(account.id, Decimal("0.00")) + movement
            elif account.account_type == "EXPENSE" and entry.transaction_date.year == now.year and entry.transaction_date.month == now.month:
                movement = debit - credit
                monthly_expenses += movement
                expense_by_account[account.id] = expense_by_account.get(account.id, Decimal("0.00")) + movement

            if account.account_type == "REVENUE" and "rental" in account.name.lower() and entry.transaction_date.date() >= (now - timedelta(days=365)).date():
                rental_income_ttm += credit - debit

        assets = Decimal("0.00")
        liabilities = Decimal("0.00")
        asset_breakdown = []
        liability_breakdown = []
        cash_accounts = []
        for account_id, balance in balances.items():
            account = accounts[account_id]
            if account.account_type == "ASSET":
                if balance >= 0:
                    assets += balance
                    asset_breakdown.append({"code": account.code, "name": account.name, "balance": balance})
                else:
                    liabilities += -balance
                    liability_breakdown.append({"code": account.code, "name": f"{account.name} Overdraft", "balance": -balance})
                if account.name in self.CASH_ACCOUNT_NAMES and balance != 0:
                    cash_accounts.append({"code": account.code, "name": account.name, "balance": balance})
            elif balance >= 0:
                liabilities += balance
                liability_breakdown.append({"code": account.code, "name": account.name, "balance": balance})
            else:
                assets += -balance
                asset_breakdown.append({"code": account.code, "name": f"{account.name} Debit Balance", "balance": -balance})

        active_loans = self.db.query(Loan).filter(Loan.user_id == self.user_id, Loan.status == "ACTIVE").all()
        bank_accounts = self.db.query(BankAccount).filter(BankAccount.user_id == self.user_id).all()
        bank_balance = sum((account.current_balance for account in bank_accounts), Decimal("0.00"))
        cards = self.db.query(CreditCardAccount).filter(CreditCardAccount.user_id == self.user_id, CreditCardAccount.is_active.is_(True)).all()
        deposits = self.db.query(Deposit).filter(Deposit.user_id == self.user_id, Deposit.status == "ACTIVE").all()
        property_assets = self.db.query(PropertyAsset).filter(PropertyAsset.user_id == self.user_id, PropertyAsset.status == "ACTIVE").all()
        card_minimum_payments = sum((
            card.minimum_monthly_payment
            if card.minimum_monthly_payment > 0
            else card.current_balance * Decimal("0.05")
            for card in cards
        ), Decimal("0.00"))
        monthly_debt_payments = sum((loan.monthly_payment for loan in active_loans), Decimal("0.00")) + card_minimum_payments
        total_credit_limit = sum((card.credit_limit for card in cards), Decimal("0.00"))
        credit_used = sum((card.current_balance for card in cards), Decimal("0.00"))
        available_credit = max(Decimal("0.00"), total_credit_limit - credit_used)
        credit_utilization = (credit_used / total_credit_limit * Decimal("100")) if total_credit_limit else Decimal("0.00")
        if monthly_income > 0:
            dbr = (monthly_debt_payments / monthly_income) * Decimal("100")
        else:
            dbr = Decimal("100") if monthly_debt_payments > 0 else Decimal("0")

        leverage = liabilities / assets if assets > 0 else Decimal("0")
        liquidity_penalty = Decimal("35") if available_cash < 0 else Decimal("0")
        score = Decimal("100") - min(Decimal("50"), dbr) - min(Decimal("30"), leverage * Decimal("40")) - liquidity_penalty
        score = max(Decimal("0"), min(Decimal("100"), score)).quantize(Decimal("1"))
        risk_level = "HIGH" if available_cash < 0 or dbr >= 40 or leverage >= Decimal("0.65") else "MODERATE" if dbr >= 25 or leverage >= Decimal("0.40") else "LOW"
        entries_by_id = {entry.id: entry for _, _, entry in rows}
        def is_current_month_flow(entry_id: int) -> bool:
            entry = entries_by_id[entry_id]
            opening_prefixes = ("opening-bank-account:", "opening-cash", "opening-inheritance:")
            legacy_bank_opening = bool(entry.related_reference and entry.related_reference.startswith("bank-account:") and entry.description.startswith("Opening balance ·"))
            is_opening_balance = bool(entry.related_reference and entry.related_reference.startswith(opening_prefixes)) or legacy_bank_opening
            return entry.transaction_date.year == now.year and entry.transaction_date.month == now.month and not is_opening_balance

        current_month_bank_changes = [change for entry_id, change in entry_bank_changes.items() if is_current_month_flow(entry_id)]
        bank_inflow = sum((change for change in current_month_bank_changes if change > 0), Decimal("0.00"))
        bank_outflow = sum((-change for change in current_month_bank_changes if change < 0), Decimal("0.00"))
        current_month_changes = [change for entry_id, change in entry_cash_changes.items() if is_current_month_flow(entry_id)]
        cash_inflow = sum((change for change in current_month_changes if change > 0), Decimal("0.00"))
        cash_outflow = sum((-change for change in current_month_changes if change < 0), Decimal("0.00"))
        recent_activity = []
        for entry in sorted(entries_by_id.values(), key=lambda item: item.transaction_date, reverse=True)[:8]:
            cash_change = entry_cash_changes.get(entry.id, Decimal("0.00"))
            recent_activity.append({"id": entry.id, "description": entry.description, "transaction_date": entry.transaction_date, "cash_change": cash_change, "related_reference": entry.related_reference})

        return {
            "total_assets": assets,
            "total_liabilities": liabilities,
            "net_worth": assets - liabilities,
            "available_cash": available_cash,
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "rental_income_ttm": rental_income_ttm,
            "real_estate_return": (rental_income_ttm / next((item["balance"] for item in asset_breakdown if item["code"] == 1210), Decimal("0.00")) * Decimal("100")).quantize(Decimal("0.1")) if any(item["code"] == 1210 and item["balance"] > 0 for item in asset_breakdown) else Decimal("0.0"),
            "income_breakdown": [{"code": accounts[account_id].code, "name": accounts[account_id].name, "balance": balance} for account_id, balance in income_by_account.items() if balance != 0],
            "expense_breakdown": [{"code": accounts[account_id].code, "name": accounts[account_id].name, "balance": balance} for account_id, balance in expense_by_account.items() if balance != 0],
            "cash_inflow": cash_inflow,
            "cash_outflow": cash_outflow,
            "net_cash_flow": cash_inflow - cash_outflow,
            "monthly_debt_payments": monthly_debt_payments,
            "credit_cards": [{"id": card.id, "issuer_bank": card.issuer_bank, "card_name": card.card_name, "last4": card.last4,
                              "credit_limit": card.credit_limit, "current_balance": card.current_balance,
                              "statement_balance": card.statement_balance,
                              "minimum_monthly_payment": card.minimum_monthly_payment,
                              "statement_cutoff_day": card.statement_cutoff_day,
                              "payment_due_day": card.payment_due_day,
                              "is_fee_free": card.is_fee_free, "annual_fee": card.annual_fee,
                              "fee_renewal_day": card.fee_renewal_day, "fee_renewal_month": card.fee_renewal_month,
                              "currency_code": card.currency_code} for card in cards],
            "credit_card_summary": {"cards_count": len(cards), "total_limit": total_credit_limit, "used": credit_used,
                                    "available": available_credit, "utilization": credit_utilization.quantize(Decimal("0.1")),
                                    "monthly_obligation": card_minimum_payments},
            "bank_accounts": [{"id": account.id, "bank_name": account.bank_name, "account_type": account.account_type,
                               "account_name": account.account_name, "account_identifier": mask_bank_account_identifier(account.account_identifier),
                               "display_name": f"{account.bank_name} {mask_bank_account_identifier(account.account_identifier)}",
                               "current_balance": account.current_balance, "currency_code": account.currency_code, "is_primary": account.is_primary} for account in bank_accounts],
            "bank_account_summary": {"accounts_count": len(bank_accounts), "total_balance": bank_balance,
                                     "monthly_inflow": bank_inflow, "monthly_outflow": bank_outflow},
            "deposits": [{column.name: getattr(deposit, column.name) for column in deposit.__table__.columns} for deposit in deposits],
            "properties": [{"id": item.acquisition_journal_entry_id, "reference": f"property:{item.acquisition_journal_entry_id}", "name": item.name, "usage": item.usage, "income_type": item.income_type, "acquisition_cost": item.current_value, "current_value": item.current_value, "purchase_date": self.db.query(JournalEntry).filter(JournalEntry.id == item.acquisition_journal_entry_id).one().transaction_date.date()} for item in property_assets],
            "dbr": dbr.quantize(Decimal("0.1")),
            "health_score": int(score),
            "risk_level": risk_level,
            "asset_breakdown": sorted(asset_breakdown, key=lambda item: item["balance"], reverse=True),
            "liability_breakdown": sorted(liability_breakdown, key=lambda item: item["balance"], reverse=True),
            "cash_accounts": sorted(cash_accounts, key=lambda item: item["balance"], reverse=True),
            "recent_activity": recent_activity,
            "accounting_period": {
                "current_period": now.strftime("%Y-%m"),
                "current_status": "SAVED" if current_close else "CURRENT",
                "last_closed_period": latest_close.period_end.strftime("%Y-%m") if latest_close else None,
            },
        }
