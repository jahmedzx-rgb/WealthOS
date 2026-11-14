from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.accounting.models.journal_entry import JournalEntry
from app.accounting.schemas.journal import JournalLineInput
from app.accounting.services.account_resolver import AccountResolver
from app.accounting.services.ledger_service import LedgerService
from app.core.models.entity import Entity
from app.core.models.user import User
from app.core.settings import settings
from app.investing.models.broker import Broker
from app.investing.models.distribution_announcement import DistributionAnnouncement
from app.investing.models.portfolio import Portfolio
from app.investing.models.position import Position
from app.investing.models.security import Security
from app.investing.models.trade import Trade
from app.investing.services.distribution_provider import (
    MultiSourceDistributionProvider,
    VerifiedFundDistributionProvider,
    VerifiedSaudiExchangeDistributionProvider,
    YahooDistributionProvider,
)


CENT = Decimal("0.01")


class DistributionTrackingService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def _eligible_quantity(self, position: Position, eligibility_date: date) -> Decimal:
        trades = self.db.query(Trade).filter(
            Trade.portfolio_id == position.portfolio_id,
            Trade.security_id == position.security_id,
            Trade.trade_date < datetime.combine(eligibility_date, datetime.max.time()),
        ).all()
        if not trades:
            return position.quantity
        return sum((trade.quantity if trade.side.upper() == "BUY" else -trade.quantity for trade in trades), Decimal("0"))

    def _settle_due_official_distributions(self) -> tuple[int, Decimal]:
        today = date.today()
        cutoff = today - timedelta(days=365)
        rows = (self.db.query(DistributionAnnouncement, Security, Portfolio)
            .join(Security, Security.id == DistributionAnnouncement.security_id)
            .join(Portfolio, Portfolio.id == DistributionAnnouncement.portfolio_id)
            .join(Entity, Entity.id == Portfolio.entity_id)
            .filter(DistributionAnnouncement.user_id == self.user_id,
                    DistributionAnnouncement.status != "RECEIVED",
                    DistributionAnnouncement.payment_date < today,
                    DistributionAnnouncement.payment_date >= cutoff)
            .all())
        resolver = AccountResolver(self.db)
        ledger = LedgerService(self.db)
        received = 0
        received_total = Decimal("0.00")
        for item, security, portfolio in rows:
            if "official" not in item.source.casefold():
                continue
            reference = f"{security.symbol}·distribution:{item.id}"
            existing = self.db.query(JournalEntry.id).filter(
                JournalEntry.user_id == self.user_id,
                JournalEntry.related_reference == reference,
            ).first()
            if existing:
                item.status = "RECEIVED"
                continue
            gross = Decimal(item.expected_gross_amount or 0).quantize(CENT, rounding=ROUND_HALF_UP)
            tax = Decimal(item.expected_tax_amount or 0).quantize(CENT, rounding=ROUND_HALF_UP)
            net = Decimal(item.expected_net_amount if item.expected_net_amount is not None else gross - tax).quantize(CENT, rounding=ROUND_HALF_UP)
            if gross <= 0 or net < 0 or gross != net + tax:
                continue
            cash_account = resolver.get_brokerage_cash_account()
            dividend_account = resolver.get_dividend_income_account()
            tax_account = resolver.get_by_name("Taxes", fallback_code=5800)
            lines = [JournalLineInput(account_id=cash_account.id, debit=net)]
            if tax:
                lines.append(JournalLineInput(account_id=tax_account.id, debit=tax))
            lines.append(JournalLineInput(account_id=dividend_account.id, credit=gross))
            portfolio.cash_balance += net
            item.status = "RECEIVED"
            ledger.post(
                user_id=self.user_id,
                description=f"{security.symbol} dividend received · {portfolio.name}",
                transaction_date=datetime.combine(item.payment_date, time.min, tzinfo=UTC),
                lines=lines,
                related_reference=reference,
            )
            received += 1
            received_total += net
        return received, received_total

    def sync(self, symbol: str | None = None) -> dict:
        user = self.db.query(User).filter(User.id == self.user_id).one()
        query = (self.db.query(Position, Security, Portfolio, Broker)
            .join(Security, Security.id == Position.security_id)
            .join(Portfolio, Portfolio.id == Position.portfolio_id)
            .outerjoin(Broker, Broker.id == Portfolio.broker_id)
            .join(Entity, Entity.id == Portfolio.entity_id)
            .filter(Entity.user_id == self.user_id, Position.quantity > 0, Security.security_type.in_(["STOCK", "ETF", "REIT", "MUTUAL_FUND"])))
        if symbol:
            query = query.filter(Security.symbol == symbol.upper())
        rows = query.all()
        created = updated = 0
        checked: list[str] = []
        for position, security, portfolio, broker in rows:
            providers = [VerifiedFundDistributionProvider()]
            if security.currency_code == "SAR":
                providers.append(VerifiedSaudiExchangeDistributionProvider())
            providers.append(YahooDistributionProvider(settings.MARKET_PRICE_REQUEST_TIMEOUT_SECONDS))
            events, sources = MultiSourceDistributionProvider(providers).get_events(security.market_symbol or security.symbol)
            checked.extend(f"{security.symbol}:{source}" for source in sources)
            if not events:
                continue
            for event in events:
                eligibility = event.eligibility_date or event.distribution_date
                quantity = max(Decimal("0"), self._eligible_quantity(position, eligibility))
                if quantity <= 0:
                    continue
                gross = (quantity * event.amount_per_unit).quantize(CENT, rounding=ROUND_HALF_UP)
                tax_rate = Decimal(str(broker.dividend_withholding_tax_rate if broker and broker.dividend_withholding_tax_rate is not None else user.default_dividend_withholding_tax_rate or 0))
                tax = (gross * tax_rate / 100).quantize(CENT, rounding=ROUND_HALF_UP)
                net = gross - tax
                fingerprint = f"{portfolio.id}:{security.id}:{eligibility.isoformat()}:{event.distribution_date.isoformat()}:{event.amount_per_unit.normalize()}"
                item = self.db.query(DistributionAnnouncement).filter_by(user_id=self.user_id, fingerprint=fingerprint).one_or_none()
                if item is None:
                    item = DistributionAnnouncement(user_id=self.user_id, portfolio_id=portfolio.id, security_id=security.id, fingerprint=fingerprint)
                    self.db.add(item); created += 1
                else:
                    updated += 1
                item.announcement_date = min(date.today(), eligibility)
                item.eligibility_date = eligibility
                item.payment_date = event.distribution_date
                item.amount_per_unit = event.amount_per_unit
                item.eligible_quantity = quantity
                item.expected_gross_amount = gross
                item.withholding_tax_rate = tax_rate
                item.expected_tax_amount = tax
                item.expected_net_amount = net
                item.currency_code = security.currency_code
                item.frequency = event.frequency
                item.source = event.source
                if item.status != "RECEIVED":
                    item.status = "AWAITING_RECEIPT" if event.distribution_date <= date.today() else "ANNOUNCED"
                item.last_checked_at = datetime.now(UTC)
        # SessionLocal disables autoflush. Persist newly discovered paid events
        # to the transaction before querying the due-payment settlement batch.
        self.db.flush()
        received, received_amount = self._settle_due_official_distributions()
        self.db.commit()
        return {"positions_checked": len(rows), "created": created, "updated": updated,
                "received": received, "received_net_amount": received_amount,
                "sources_checked": checked}

    def list(self, days: int = 730, include_received: bool = True) -> list[dict]:
        query = (self.db.query(DistributionAnnouncement, Security, Portfolio)
            .join(Security, Security.id == DistributionAnnouncement.security_id)
            .join(Portfolio, Portfolio.id == DistributionAnnouncement.portfolio_id)
            .filter(DistributionAnnouncement.user_id == self.user_id,
                    DistributionAnnouncement.payment_date >= date.today().replace(year=date.today().year - 1))
            .order_by(DistributionAnnouncement.payment_date.desc()))
        if not include_received:
            query = query.filter(DistributionAnnouncement.status != "RECEIVED")
        return [{
            "announcement_id": item.id, "position_id": position.id if (position := self.db.query(Position).filter_by(portfolio_id=item.portfolio_id, security_id=item.security_id).first()) else 0,
            "security_id": security.id, "symbol": security.symbol, "name": security.name,
            "portfolio_id": portfolio.id, "portfolio_name": portfolio.name,
            "announcement_date": item.announcement_date, "eligibility_date": item.eligibility_date,
            "distribution_date": item.payment_date, "payment_date": item.payment_date,
            "amount_per_unit": item.amount_per_unit, "eligible_quantity": item.eligible_quantity,
            "expected_amount": item.expected_gross_amount, "withholding_tax_rate": item.withholding_tax_rate,
            "expected_tax_amount": item.expected_tax_amount, "expected_net_amount": item.expected_net_amount,
            "currency_code": item.currency_code, "frequency": item.frequency, "source": item.source,
            "status": item.status, "days_until": (item.payment_date - date.today()).days,
        } for item, security, portfolio in query.all()]
