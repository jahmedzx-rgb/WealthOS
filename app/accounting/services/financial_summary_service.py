from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
import re

from sqlalchemy import func, inspect
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
from app.accounting.services.card_statement_service import statement_view
from app.investing.models.portfolio import Portfolio
from app.investing.models.distribution_announcement import DistributionAnnouncement
from app.investing.models.position import Position
from app.investing.models.security import Security
from app.core.models.entity import Entity


class FinancialSummaryService:
    CASH_ACCOUNT_NAMES = {"Cash", "Cash on Hand", "Bank Accounts", "Primary Bank Account", "Brokerage Cash", "Digital Wallets", "Foreign Currency Cash"}

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    @staticmethod
    def _deposit_return_status(reference: str, deposit_statuses: dict[int, str]) -> str | None:
        if reference.startswith("deposit-maturity:") and reference.endswith(":income"):
            return "REALIZED"
        if not reference.startswith("deposit-return:"):
            return None
        try:
            deposit_id = int(reference.split(":", 1)[1])
        except (TypeError, ValueError):
            return "ACCRUED"
        return "REALIZED" if deposit_statuses.get(deposit_id) in {"CLOSED", "RENEWED"} else "ACCRUED"

    def _setup_activities(self) -> list[dict]:
        """Return administrative channel creation events with no financial impact."""
        inspector = inspect(self.db.get_bind())
        activity: list[dict] = []

        def add(item_id: int, description: str, created_at: datetime, reference: str, detail: str, url: str, currency_code: str | None = None) -> None:
            activity.append({"id": -item_id, "description": description, "transaction_date": created_at,
                "cash_change": Decimal("0.00"), "display_amount": Decimal("0.00"),
                "related_reference": reference, "account_detail": detail, "activity_url": url,
                "currency_code": currency_code})

        if inspector.has_table(BankAccount.__tablename__):
            for account in self.db.query(BankAccount).filter(BankAccount.user_id == self.user_id).all():
                add(account.id, f"Bank account opened · {account.account_name}", account.created_at,
                    f"bank-account-created:{account.id}", f"{account.bank_name} · {mask_bank_account_identifier(account.account_identifier)}", "/bank-accounts")
        if inspector.has_table(CreditCardAccount.__tablename__):
            for card in self.db.query(CreditCardAccount).filter(CreditCardAccount.user_id == self.user_id).all():
                add(card.id, f"Credit card added · {card.card_name}", card.created_at,
                    f"credit-card-created:{card.id}", f"{card.issuer_bank} · •• {card.last4}", "/credit-cards")
        if inspector.has_table(Deposit.__tablename__):
            for deposit in self.db.query(Deposit).filter(Deposit.user_id == self.user_id).all():
                add(deposit.id, f"Deposit opened · {deposit.product_name}", deposit.created_at,
                    f"deposit-created:{deposit.id}", f"{deposit.provider_name} · Deposit", "/investing/deposits")
        # Focused accounting tests may intentionally omit the investing schema.
        if inspector.has_table(Portfolio.__tablename__) and inspector.has_table(Entity.__tablename__):
            portfolios = self.db.query(Portfolio).join(Entity, Portfolio.entity_id == Entity.id).filter(Entity.user_id == self.user_id).all()
            for portfolio in portfolios:
                add(portfolio.id, f"Portfolio opened · {portfolio.name}", portfolio.created_at,
                    f"portfolio-created:{portfolio.id}", f"{portfolio.broker.name} · Portfolio" if portfolio.broker else "Portfolio", "/investing/brokers",
                    portfolio.base_currency.code)
        return activity

    @staticmethod
    def _portfolio_activity_currency(reference: str, currencies: dict[int, str]) -> str | None:
        if not reference.startswith(("opening-portfolio:", "opening-portfolio-adjustment:", "portfolio:")):
            return None
        try:
            portfolio_id = int(reference.split(":", 2)[1])
        except (IndexError, ValueError):
            return None
        return currencies.get(portfolio_id)

    def _portfolio_currencies(self) -> dict[int, str]:
        inspector = inspect(self.db.get_bind())
        if not inspector.has_table(Portfolio.__tablename__) or not inspector.has_table(Entity.__tablename__):
            return {}
        return {portfolio.id: portfolio.base_currency.code for portfolio in self.db.query(Portfolio).join(Entity, Portfolio.entity_id == Entity.id).filter(Entity.user_id == self.user_id).all()}

    def _activity_currency(self, reference: str, description: str, portfolio_currencies: dict[int, str],
                           distribution_metadata: dict[int, tuple[int, str]], security_currencies: dict[str, str]) -> str | None:
        portfolio_currency = self._portfolio_activity_currency(reference, portfolio_currencies)
        if portfolio_currency:
            return portfolio_currency
        marker = "·distribution:"
        if marker in reference:
            try:
                announcement = distribution_metadata.get(int(reference.split(marker, 1)[1]))
            except ValueError:
                announcement = None
            if announcement:
                return announcement[1]
        prefix_symbol = reference.split("·", 1)[0].strip().upper()
        if prefix_symbol in security_currencies:
            return security_currencies[prefix_symbol]
        searchable_text = f"{reference} {description or ''}".upper()
        return next((currency for symbol, currency in security_currencies.items()
                     if len(symbol) >= 2 and re.search(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", searchable_text)), None)

    def _distribution_activity_metadata(self) -> tuple[dict[int, tuple[int, str]], dict[str, str]]:
        inspector = inspect(self.db.get_bind())
        announcements = ({item.id: (item.portfolio_id, item.currency_code)
                          for item in self.db.query(DistributionAnnouncement).filter(DistributionAnnouncement.user_id == self.user_id).all()}
                         if inspector.has_table(DistributionAnnouncement.__tablename__) else {})
        securities = ({item.symbol.upper(): item.currency_code for item in self.db.query(Security).all()}
                      if inspector.has_table(Security.__tablename__) else {})
        return announcements, securities

    def activity_for_month(self, year: int, month: int) -> list[dict]:
        if month < 1 or month > 12 or year < 1900 or year > 9999:
            raise ValueError("Invalid activity month.")
        local_tz = timezone(timedelta(hours=3))
        start = datetime(year, month, 1, tzinfo=local_tz)
        end = datetime(year + 1, 1, 1, tzinfo=local_tz) if month == 12 else datetime(year, month + 1, 1, tzinfo=local_tz)
        rows = (
            self.db.query(JournalLine, Account, JournalEntry)
            .join(Account, JournalLine.account_id == Account.id)
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .filter(JournalEntry.user_id == self.user_id, JournalEntry.transaction_date >= start, JournalEntry.transaction_date < end)
            .all()
        )
        entries = {entry.id: entry for _, _, entry in rows}
        cash_changes: dict[int, Decimal] = {}
        asset_changes: dict[int, Decimal] = {}
        income_changes: dict[int, Decimal] = {}
        expense_changes: dict[int, Decimal] = {}
        entry_debits: dict[int, Decimal] = {}
        for line, account, entry in rows:
            debit = line.debit or Decimal("0.00")
            credit = line.credit or Decimal("0.00")
            entry_debits[entry.id] = entry_debits.get(entry.id, Decimal("0.00")) + debit
            if account.account_type == "ASSET" and account.name in self.CASH_ACCOUNT_NAMES:
                cash_changes[entry.id] = cash_changes.get(entry.id, Decimal("0.00")) + debit - credit
                asset_changes[entry.id] = asset_changes.get(entry.id, Decimal("0.00")) + debit - credit
            elif account.account_type == "ASSET":
                asset_changes[entry.id] = asset_changes.get(entry.id, Decimal("0.00")) + debit - credit
            elif account.account_type == "REVENUE":
                income_changes[entry.id] = income_changes.get(entry.id, Decimal("0.00")) + credit - debit
            elif account.account_type == "EXPENSE":
                expense_changes[entry.id] = expense_changes.get(entry.id, Decimal("0.00")) + debit - credit
        cards = {card.id: card for card in self.db.query(CreditCardAccount).filter(CreditCardAccount.user_id == self.user_id).all()}
        deposit_statuses = {deposit.id: deposit.status for deposit in self.db.query(Deposit).filter(Deposit.user_id == self.user_id).all()}
        portfolio_currencies = self._portfolio_currencies()
        distribution_activity_metadata, security_currencies = self._distribution_activity_metadata()
        activity = []
        for entry in sorted(entries.values(), key=lambda item: (item.transaction_date, item.id), reverse=True):
            reference = entry.related_reference or ""
            cash_change = cash_changes.get(entry.id, Decimal("0.00"))
            income_change = income_changes.get(entry.id, Decimal("0.00"))
            expense_change = expense_changes.get(entry.id, Decimal("0.00"))
            display_amount = cash_change if "·distribution:" in reference else entry_debits.get(entry.id, Decimal("0.00")) if reference.startswith(("credit-card-sadad:", "historical-portfolio-movement:")) else asset_changes.get(entry.id, Decimal("0.00")) if reference.startswith(("opening-portfolio:", "opening-portfolio-adjustment:")) else income_change if income_change else -expense_change if expense_change else cash_change
            account_detail = None
            if reference.startswith(("credit-card-expense:", "credit-card-cashback:")):
                try:
                    card = cards.get(int(reference.rsplit(":", 1)[1]))
                    if card is not None:
                        account_detail = f"Credit Cards · {card.issuer_bank} •• {card.last4}"
                except ValueError:
                    pass
            activity.append({"id": entry.id, "description": entry.description, "transaction_date": entry.transaction_date, "cash_change": cash_change, "display_amount": display_amount, "related_reference": entry.related_reference, "account_detail": account_detail, "currency_code": self._activity_currency(reference, entry.description, portfolio_currencies, distribution_activity_metadata, security_currencies), "return_status": self._deposit_return_status(reference, deposit_statuses)})
        activity.extend(item for item in self._setup_activities() if item["transaction_date"].year == year and item["transaction_date"].month == month)
        return sorted(activity, key=lambda item: (item["transaction_date"].replace(tzinfo=None), item["id"]), reverse=True)

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
        entry_asset_changes: dict[int, Decimal] = {}
        entry_bank_changes: dict[int, Decimal] = {}
        entry_income_changes: dict[int, Decimal] = {}
        entry_expense_changes: dict[int, Decimal] = {}
        entry_debits: dict[int, Decimal] = {}
        rental_income_ttm = Decimal("0.00")
        investment_distributions_total = Decimal("0.00")
        investment_distributions_by_symbol: dict[str, Decimal] = {}
        investment_distributions_by_symbol_currency: dict[str, dict[str, Decimal]] = {}
        investment_distributions_by_portfolio_currency: dict[str, dict[str, Decimal]] = {}
        investment_distributions_by_currency: dict[str, Decimal] = {}
        inspector = inspect(self.db.get_bind())
        distribution_metadata: dict[int, tuple[int, str]] = {}
        distribution_security_metadata: dict[str, tuple[str, list[int]]] = {}
        if inspector.has_table(DistributionAnnouncement.__tablename__):
            distribution_metadata = {item.id: (item.portfolio_id, item.currency_code) for item in self.db.query(DistributionAnnouncement).filter(DistributionAnnouncement.user_id == self.user_id).all()}
        if inspector.has_table(Security.__tablename__):
            distribution_security_metadata = {security.symbol.upper(): (security.currency_code, []) for security in self.db.query(Security).all()}
        if all(inspector.has_table(table) for table in (Position.__tablename__, Security.__tablename__, Portfolio.__tablename__, Entity.__tablename__)):
            security_rows = (self.db.query(Security, Position.portfolio_id)
                .join(Position, Position.security_id == Security.id)
                .join(Portfolio, Portfolio.id == Position.portfolio_id)
                .join(Entity, Entity.id == Portfolio.entity_id)
                .filter(Entity.user_id == self.user_id)
                .all())
            for security, portfolio_id in security_rows:
                currency, portfolio_ids = distribution_security_metadata.setdefault(security.symbol.upper(), (security.currency_code, []))
                if portfolio_id not in portfolio_ids:
                    portfolio_ids.append(portfolio_id)
        realized_price_return_total = Decimal("0.00")
        realized_price_return_by_portfolio: dict[str, Decimal] = {}

        for line, account, entry in rows:
            debit = line.debit or Decimal("0.00")
            credit = line.credit or Decimal("0.00")
            entry_debits[entry.id] = entry_debits.get(entry.id, Decimal("0.00")) + debit
            accounts[account.id] = account
            if account.account_type == "ASSET":
                balance = debit - credit
                balances[account.id] = balances.get(account.id, Decimal("0.00")) + balance
                entry_asset_changes[entry.id] = entry_asset_changes.get(entry.id, Decimal("0.00")) + balance
                if account.name in self.CASH_ACCOUNT_NAMES:
                    available_cash += balance
                    entry_cash_changes[entry.id] = entry_cash_changes.get(entry.id, Decimal("0.00")) + balance
                if account.code == 1120:
                    entry_bank_changes[entry.id] = entry_bank_changes.get(entry.id, Decimal("0.00")) + balance
            elif account.account_type == "LIABILITY":
                balances[account.id] = balances.get(account.id, Decimal("0.00")) + credit - debit
            elif account.account_type == "REVENUE":
                movement = credit - debit
                if account.name.strip().casefold() in {"dividend income", "investment distributions", "distribution income"}:
                    investment_distributions_total += movement
                    reference_symbol = (entry.related_reference or "").split("·", 1)[0].strip().upper()
                    reference = entry.related_reference or ""
                    distribution_symbol = reference_symbol if reference_symbol in distribution_security_metadata else next((
                        symbol for symbol in distribution_security_metadata
                        if len(symbol) >= 2 and re.search(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", f"{reference} {entry.description or ''}".upper())
                    ), "")
                    if distribution_symbol:
                        investment_distributions_by_symbol[distribution_symbol] = investment_distributions_by_symbol.get(distribution_symbol, Decimal("0.00")) + movement
                    marker = "·distribution:"
                    distribution_currency = None
                    distribution_portfolio_id = None
                    if marker in reference:
                        try:
                            metadata = distribution_metadata.get(int(reference.split(marker, 1)[1]))
                        except ValueError:
                            metadata = None
                        if metadata:
                            distribution_portfolio_id, distribution_currency = metadata
                    if distribution_currency is None and distribution_symbol in distribution_security_metadata:
                        distribution_currency, matching_portfolios = distribution_security_metadata[distribution_symbol]
                        # A symbol identifies its currency; associate it with a portfolio only when the ledger
                        # reference names that portfolio or the symbol is held in exactly one portfolio.
                        if distribution_portfolio_id is None:
                            if "reinvested-distribution:" in reference:
                                try:
                                    distribution_portfolio_id = int(reference.split("reinvested-distribution:", 1)[1].split(":", 1)[0])
                                except ValueError:
                                    distribution_portfolio_id = None
                            elif len(matching_portfolios) == 1:
                                distribution_portfolio_id = matching_portfolios[0]
                    if distribution_currency:
                        investment_distributions_by_currency[distribution_currency] = investment_distributions_by_currency.get(distribution_currency, Decimal("0.00")) + movement
                        symbol_totals = investment_distributions_by_symbol_currency.setdefault(distribution_symbol, {})
                        symbol_totals[distribution_currency] = symbol_totals.get(distribution_currency, Decimal("0.00")) + movement
                        if distribution_portfolio_id is not None:
                            portfolio_key = str(distribution_portfolio_id)
                            currency_totals = investment_distributions_by_portfolio_currency.setdefault(portfolio_key, {})
                            currency_totals[distribution_currency] = currency_totals.get(distribution_currency, Decimal("0.00")) + movement
                reference_parts = (entry.related_reference or "").split(":")
                if account.code == 4600 and len(reference_parts) >= 2 and reference_parts[0] == "portfolio":
                    portfolio_key = reference_parts[1]
                    realized_price_return_total += movement
                    realized_price_return_by_portfolio[portfolio_key] = realized_price_return_by_portfolio.get(portfolio_key, Decimal("0.00")) + movement
                if entry.transaction_date.year == now.year and entry.transaction_date.month == now.month:
                    monthly_income += movement
                    income_by_account[account.id] = income_by_account.get(account.id, Decimal("0.00")) + movement
                    entry_income_changes[entry.id] = entry_income_changes.get(entry.id, Decimal("0.00")) + movement
            elif account.account_type == "EXPENSE":
                movement = debit - credit
                reference_parts = (entry.related_reference or "").split(":")
                if account.code == 5690 and len(reference_parts) >= 2 and reference_parts[0] == "portfolio":
                    portfolio_key = reference_parts[1]
                    realized_price_return_total -= movement
                    realized_price_return_by_portfolio[portfolio_key] = realized_price_return_by_portfolio.get(portfolio_key, Decimal("0.00")) - movement
                entry_expense_changes[entry.id] = entry_expense_changes.get(entry.id, Decimal("0.00")) + movement
                if entry.transaction_date.year == now.year and entry.transaction_date.month == now.month:
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
        bank_accounts = self.db.query(BankAccount).filter(BankAccount.user_id == self.user_id, BankAccount.account_type != "DIGITAL_WALLET").all()
        bank_balance = sum((account.current_balance for account in bank_accounts), Decimal("0.00"))
        cards = self.db.query(CreditCardAccount).filter(CreditCardAccount.user_id == self.user_id, CreditCardAccount.is_active.is_(True)).all()
        deposits = self.db.query(Deposit).filter(Deposit.user_id == self.user_id, Deposit.status.in_(["ACTIVE", "MATURED"])).all()
        property_assets = self.db.query(PropertyAsset).filter(PropertyAsset.user_id == self.user_id, PropertyAsset.status == "ACTIVE").all()
        card_minimum_payments = sum((
            Decimal("0.00") if card.current_balance <= 0
            else card.minimum_monthly_payment
            if card.minimum_monthly_payment > 0
            else card.current_balance * Decimal("0.05")
            for card in cards
        ), Decimal("0.00"))
        monthly_debt_payments = sum((loan.monthly_payment for loan in active_loans), Decimal("0.00")) + card_minimum_payments
        total_credit_limit = sum((card.credit_limit for card in cards), Decimal("0.00"))
        credit_used = sum((card.current_balance for card in cards), Decimal("0.00"))
        cards_by_id = {card.id: card for card in cards}
        deposit_statuses = {deposit.id: deposit.status for deposit in self.db.query(Deposit).filter(Deposit.user_id == self.user_id).all()}
        portfolio_currencies = self._portfolio_currencies()
        distribution_activity_metadata, security_currencies = self._distribution_activity_metadata()
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
            opening_prefixes = ("opening-bank-account:", "opening-bank-account-adjustment:", "opening-cash", "opening-inheritance:", "opening-historical-link:", "opening-portfolio:", "opening-portfolio-adjustment:")
            legacy_bank_opening = bool(entry.related_reference and entry.related_reference.startswith("bank-account:") and entry.description.startswith("Opening balance ·"))
            is_opening_balance = bool(entry.related_reference and entry.related_reference.startswith(opening_prefixes)) or legacy_bank_opening
            reference = entry.related_reference or ""
            is_principal_transfer = reference.startswith("deposit-withdrawal:") or (
                reference.startswith("deposit-maturity:") and reference.endswith(":principal-return")
            )
            return entry.transaction_date.year == now.year and entry.transaction_date.month == now.month and not is_opening_balance and not is_principal_transfer

        current_month_bank_changes = [change for entry_id, change in entry_bank_changes.items() if is_current_month_flow(entry_id)]
        bank_inflow = sum((change for change in current_month_bank_changes if change > 0), Decimal("0.00"))
        bank_outflow = sum((-change for change in current_month_bank_changes if change < 0), Decimal("0.00"))
        current_month_changes = [change for entry_id, change in entry_cash_changes.items() if is_current_month_flow(entry_id)]
        cash_inflow = sum((change for change in current_month_changes if change > 0), Decimal("0.00"))
        cash_outflow = sum((-change for change in current_month_changes if change < 0), Decimal("0.00"))
        recent_activity = []
        for entry in sorted(entries_by_id.values(), key=lambda item: item.transaction_date, reverse=True)[:8]:
            cash_change = entry_cash_changes.get(entry.id, Decimal("0.00"))
            reference = entry.related_reference or ""
            income_change = entry_income_changes.get(entry.id, Decimal("0.00"))
            expense_change = entry_expense_changes.get(entry.id, Decimal("0.00"))
            display_amount = cash_change if "·distribution:" in reference else entry_debits.get(entry.id, Decimal("0.00")) if reference.startswith(("credit-card-sadad:", "historical-portfolio-movement:")) else entry_asset_changes.get(entry.id, Decimal("0.00")) if reference.startswith(("opening-portfolio:", "opening-portfolio-adjustment:")) else income_change if income_change else -expense_change if expense_change else cash_change
            account_detail = None
            if reference.startswith(("credit-card-expense:", "credit-card-cashback:")):
                try:
                    card = cards_by_id.get(int(reference.rsplit(":", 1)[1]))
                    if card is not None:
                        account_detail = f"Credit Cards · {card.issuer_bank} •• {card.last4}"
                except ValueError:
                    pass
            recent_activity.append({"id": entry.id, "description": entry.description, "transaction_date": entry.transaction_date, "cash_change": cash_change, "display_amount": display_amount, "related_reference": entry.related_reference, "account_detail": account_detail, "currency_code": self._activity_currency(reference, entry.description, portfolio_currencies, distribution_activity_metadata, security_currencies), "return_status": self._deposit_return_status(reference, deposit_statuses)})

        recent_activity.extend(self._setup_activities())
        recent_activity = sorted(recent_activity, key=lambda item: (item["transaction_date"].replace(tzinfo=None), item["id"]), reverse=True)[:8]

        return {
            "total_assets": assets,
            "total_liabilities": liabilities,
            "net_worth": assets - liabilities,
            "available_cash": available_cash,
            "monthly_income": monthly_income,
            "investment_distributions_total": investment_distributions_total,
            "investment_distributions_by_symbol": investment_distributions_by_symbol,
            "investment_distributions_by_symbol_currency": investment_distributions_by_symbol_currency,
            "investment_distributions_by_portfolio_currency": investment_distributions_by_portfolio_currency,
            "investment_distributions_by_currency": investment_distributions_by_currency,
            "realized_price_return_total": realized_price_return_total,
            "realized_price_return_by_portfolio": realized_price_return_by_portfolio,
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
                              "payment_due_date": card.payment_due_date,
                              "statement_cutoff_date": card.statement_cutoff_date,
                              "is_fee_free": card.is_fee_free, "annual_fee": card.annual_fee,
                              "fee_renewal_day": card.fee_renewal_day, "fee_renewal_month": card.fee_renewal_month,
                              "currency_code": card.currency_code, **statement_view(self.db, card)} for card in cards],
            "credit_card_summary": {"cards_count": len(cards), "total_limit": total_credit_limit, "used": credit_used,
                                    "available": available_credit, "utilization": credit_utilization.quantize(Decimal("0.1")),
                                    "monthly_obligation": card_minimum_payments},
            "bank_accounts": [{"id": account.id, "bank_name": account.bank_name, "account_type": account.account_type,
                               "account_name": account.account_name, "account_identifier": mask_bank_account_identifier(account.account_identifier),
                               "display_name": f"{account.bank_name} {mask_bank_account_identifier(account.account_identifier)}",
                               "current_balance": account.current_balance, "currency_code": account.currency_code, "is_primary": account.is_primary} for account in bank_accounts],
            "bank_account_summary": {"accounts_count": len(bank_accounts), "total_balance": bank_balance,
                                     "monthly_inflow": bank_inflow, "monthly_outflow": bank_outflow},
            "deposits": [{**{column.name: getattr(deposit, column.name) for column in deposit.__table__.columns}, "actual_return": (self.db.query(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), 0)).join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id).join(Account, JournalLine.account_id == Account.id).filter(JournalEntry.user_id == self.user_id, JournalEntry.related_reference == f"deposit-return:{deposit.id}", Account.code == 4400).scalar() if deposit.product_type == "INCOME_SAVINGS" else deposit.actual_return), "standard_annual_return_rate": deposit.annual_return_rate, "annual_return_rate": deposit.effective_annual_return_rate, "accrual_start_date": ((self.db.query(JournalEntry).filter(JournalEntry.user_id == self.user_id, JournalEntry.related_reference.in_([f"deposit-return:{deposit.id}", f"deposit-withdrawal:{deposit.id}"])).order_by(JournalEntry.transaction_date.desc()).first().transaction_date.date()) if self.db.query(JournalEntry).filter(JournalEntry.user_id == self.user_id, JournalEntry.related_reference.in_([f"deposit-return:{deposit.id}", f"deposit-withdrawal:{deposit.id}"])).order_by(JournalEntry.transaction_date.desc()).first() else deposit.start_date)} for deposit in deposits],
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
