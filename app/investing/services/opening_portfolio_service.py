from datetime import UTC, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.schemas.journal import JournalLineInput
from app.accounting.services.account_resolver import AccountResolver
from app.accounting.services.investment_account_resolver import InvestmentAccountResolver
from app.accounting.services.ledger_service import LedgerService
from app.investing.models.position import Position
from app.investing.models.security import Security
from app.investing.services.market_price_service import MarketPriceService
from app.investing.services.portfolio_service import PortfolioService


class OpeningPortfolioService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    @staticmethod
    def _market_price_date(security: Security, as_of_date: datetime) -> datetime:
        if (security.exchange or "").upper() not in {"SAUDI_EXCHANGE", "TADAWUL"}:
            return as_of_date
        riyadh = timezone(timedelta(hours=3))
        local = as_of_date.astimezone(riyadh) if as_of_date.tzinfo else as_of_date.replace(tzinfo=riyadh)
        if local.weekday() == 4:
            local -= timedelta(days=1)
        elif local.weekday() == 5:
            local -= timedelta(days=2)
        local = datetime.combine(local.date(), time(15), tzinfo=riyadh)
        return local.astimezone(UTC).replace(tzinfo=None)

    def record(self, *, portfolio_id: int, cash_balance: Decimal, positions: list[dict], as_of_date: datetime):
        portfolio = PortfolioService(self.db).get(portfolio_id, self.user_id)
        if portfolio.cash_balance != 0 or self.db.query(Position.id).filter(Position.portfolio_id == portfolio.id, Position.quantity != 0).first():
            raise ValueError("Opening portfolio balance can only be recorded for an empty portfolio.")
        if cash_balance < 0 or not positions:
            raise ValueError("Enter at least one historical position and a non-negative cash balance.")

        investment_resolver = InvestmentAccountResolver(self.db)
        ledger_totals: dict[int, Decimal] = {}
        recorded: list[Position] = []
        total_cost = Decimal("0")
        seen: set[int] = set()
        for item in positions:
            security_id = int(item["security_id"])
            if security_id in seen:
                raise ValueError("Each security can appear only once in an opening portfolio balance.")
            seen.add(security_id)
            security = self.db.query(Security).filter(Security.id == security_id, Security.is_active.is_(True)).first()
            if security is None:
                raise ValueError("Select a valid security.")
            if security.currency_code != portfolio.base_currency.code:
                raise ValueError("Every opening position must use the portfolio currency.")
            quantity = Decimal(item["quantity"])
            position_cost = Decimal(item["total_cost"])
            market_price = Decimal(item["market_price"])
            is_option = security.security_type == "OPTION"
            if market_price <= 0 or quantity == 0 or position_cost == 0:
                raise ValueError("Quantity and historical cost must be non-zero, and current market price must be greater than zero.")
            if not is_option and (quantity < 0 or position_cost < 0):
                raise ValueError("Only option positions can use negative quantity and historical cost.")
            if (quantity > 0) != (position_cost > 0):
                raise ValueError("Position quantity and historical cost must use the same sign.")
            multiplier = Decimal("100") if is_option else Decimal("1")
            position = Position(
                portfolio_id=portfolio.id,
                security_id=security.id,
                quantity=quantity,
                average_cost=position_cost / quantity / multiplier,
                fair_value=None,
            )
            self.db.add(position)
            MarketPriceService(self.db).record(security.id, market_price, self._market_price_date(security, as_of_date))
            investment_account = investment_resolver.resolve(security)
            ledger_totals[investment_account.id] = ledger_totals.get(investment_account.id, Decimal("0")) + position_cost
            total_cost += position_cost
            recorded.append(position)

        portfolio.cash_balance = cash_balance
        lines = [JournalLineInput(account_id=account_id, debit=amount) if amount > 0 else JournalLineInput(account_id=account_id, credit=-amount) for account_id, amount in ledger_totals.items() if amount]
        if cash_balance:
            lines.append(JournalLineInput(account_id=investment_resolver.get_brokerage_cash_account().id, debit=cash_balance))
        opening_value = total_cost + cash_balance
        if opening_value > 0:
            lines.append(JournalLineInput(account_id=AccountResolver(self.db).get_by_code(3150).id, credit=opening_value))
        elif opening_value < 0:
            lines.append(JournalLineInput(account_id=AccountResolver(self.db).get_by_code(3150).id, debit=-opening_value))
        entry = LedgerService(self.db).post(
            user_id=self.user_id,
            description=f"Opening portfolio balance · {portfolio.name}",
            transaction_date=as_of_date,
            lines=lines,
            related_reference=f"opening-portfolio:{portfolio.id}",
        )
        self.db.commit()
        return portfolio, recorded, entry

    def correct(self, *, portfolio_id: int, cash_balance: Decimal, positions: list[dict], as_of_date: datetime):
        portfolio = PortfolioService(self.db).get(portfolio_id, self.user_id)
        existing = {item.security_id: item for item in self.db.query(Position).filter(Position.portfolio_id == portfolio.id).all()}
        if not existing:
            raise ValueError("Record the opening portfolio balance before correcting it.")
        if cash_balance < 0 or not positions:
            raise ValueError("Enter at least one historical position and a non-negative cash balance.")

        investment_resolver = InvestmentAccountResolver(self.db)
        account_deltas: dict[int, Decimal] = {}
        seen: set[int] = set()
        for item in positions:
            security_id = int(item["security_id"])
            if security_id in seen:
                raise ValueError("Each security can appear only once in an opening portfolio balance.")
            seen.add(security_id)
            security = self.db.query(Security).filter(Security.id == security_id, Security.is_active.is_(True)).first()
            if security is None or security.currency_code != portfolio.base_currency.code:
                raise ValueError("Select a valid security in the portfolio currency.")
            quantity, desired_cost, market_price = Decimal(item["quantity"]), Decimal(item["total_cost"]), Decimal(item["market_price"])
            is_option = security.security_type == "OPTION"
            if market_price <= 0 or quantity == 0 or desired_cost == 0:
                raise ValueError("Quantity and historical cost must be non-zero, and current market price must be greater than zero.")
            if not is_option and (quantity < 0 or desired_cost < 0):
                raise ValueError("Only option positions can use negative quantity and historical cost.")
            if (quantity > 0) != (desired_cost > 0):
                raise ValueError("Position quantity and historical cost must use the same sign.")
            multiplier = Decimal("100") if is_option else Decimal("1")
            current = existing.get(security_id)
            old_cost = (current.quantity * current.average_cost * multiplier).quantize(Decimal("0.01")) if current else Decimal("0")
            delta = desired_cost - old_cost
            account = investment_resolver.resolve(security)
            account_deltas[account.id] = account_deltas.get(account.id, Decimal("0")) + delta
            if current:
                current.quantity, current.average_cost = quantity, desired_cost / quantity / multiplier
            else:
                self.db.add(Position(portfolio_id=portfolio.id, security_id=security.id, quantity=quantity, average_cost=desired_cost / quantity / multiplier, fair_value=None))
            MarketPriceService(self.db).record(security.id, market_price, self._market_price_date(security, as_of_date))

        if set(existing) - seen:
            raise ValueError("Keep all existing positions when correcting the opening portfolio balance.")
        cash_delta = cash_balance - portfolio.cash_balance
        portfolio.cash_balance = cash_balance
        lines: list[JournalLineInput] = []
        for account_id, delta in account_deltas.items():
            if delta > 0:
                lines.append(JournalLineInput(account_id=account_id, debit=delta))
            elif delta < 0:
                lines.append(JournalLineInput(account_id=account_id, credit=-delta))
        if cash_delta > 0:
            lines.append(JournalLineInput(account_id=investment_resolver.get_brokerage_cash_account().id, debit=cash_delta))
        elif cash_delta < 0:
            lines.append(JournalLineInput(account_id=investment_resolver.get_brokerage_cash_account().id, credit=-cash_delta))
        net_delta = sum(account_deltas.values(), Decimal("0")) + cash_delta
        if net_delta > 0:
            lines.append(JournalLineInput(account_id=AccountResolver(self.db).get_by_code(3150).id, credit=net_delta))
        elif net_delta < 0:
            lines.append(JournalLineInput(account_id=AccountResolver(self.db).get_by_code(3150).id, debit=-net_delta))
        if not lines:
            self.db.commit()
            return portfolio, None
        entry = LedgerService(self.db).post(user_id=self.user_id,
            description=f"Opening portfolio balance correction · {portfolio.name}", transaction_date=as_of_date,
            lines=lines, related_reference=f"opening-portfolio-adjustment:{portfolio.id}")
        self.db.commit()
        return portfolio, entry
