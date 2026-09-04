from sqlalchemy.orm import Session
from uuid import uuid4
from decimal import Decimal

from app.investing.models.broker import Broker
from app.investing.models.portfolio import Portfolio
from app.investing.models.position import Position
from app.investing.models.security import Security
from app.core.models.entity import Entity
from app.accounting.schemas.journal import JournalLineInput
from app.accounting.services.account_resolver import AccountResolver
from app.accounting.services.investment_account_resolver import InvestmentAccountResolver
from app.accounting.services.ledger_service import LedgerService
from app.investing.services.broker_catalog import broker_match, effective_commission_rate, effective_commission_source, effective_vat_rate, effective_vat_source


class BrokerService:
    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.user_id = user_id

    def list(self) -> list[Broker]:
        return (
            self.db.query(Broker)
            .filter(Broker.user_id == self.user_id, Broker.is_active.is_(True))
            .order_by(Broker.name)
            .all()
        )

    def get(self, broker_id: int) -> Broker:
        broker = (
            self.db.query(Broker)
            .filter(Broker.id == broker_id, Broker.user_id == self.user_id)
            .first()
        )

        if broker is None:
            raise ValueError(
                f"Broker {broker_id} not found."
            )

        return broker

    def create(
        self,
        *,
        name: str,
        country: str | None = None,
        website: str | None = None,
        commission_rate: Decimal | None = None,
        commission_tax_rate: Decimal | None = None,
        dividend_withholding_tax_rate: Decimal | None = None,
    ) -> Broker:
        catalog_item, exact_catalog_match = broker_match(name)
        if catalog_item is not None and not exact_catalog_match:
            raise ValueError(f'Did you mean "{catalog_item.name}"? Select it from the broker list.')
        if catalog_item is not None:
            name = catalog_item.name
            country = catalog_item.country
            website = catalog_item.website
            institution_name = catalog_item.institution_name
            execution_partner = catalog_item.execution_partner
            commission_rate = commission_rate if commission_rate is not None else effective_commission_rate(catalog_item)
            commission_tax_rate = commission_tax_rate if commission_tax_rate is not None else effective_vat_rate(catalog_item)
        if commission_rate is None:
            raise ValueError("Enter the broker commission rate before saving.")
        if commission_tax_rate is None:
            raise ValueError("Enter the VAT rate applied to the brokerage service before saving.")
        existing = (
            self.db.query(Broker)
            .filter(Broker.user_id == self.user_id, Broker.name.ilike(name))
            .first()
        )
        if existing is not None:
            raise ValueError(
                "A broker with this name already exists."
            )

        code = f"BRK-{uuid4().hex[:8].upper()}"
        broker = Broker(
            user_id=self.user_id,
            code=code,
            name=name,
            country=country,
            website=website,
            institution_name=institution_name if catalog_item is not None else name,
            execution_partner=execution_partner if catalog_item is not None else None,
            commission_rate=commission_rate,
            commission_source=effective_commission_source(catalog_item) if catalog_item and commission_rate == effective_commission_rate(catalog_item) else "User supplied",
            commission_tax_rate=commission_tax_rate,
            commission_tax_source=effective_vat_source(catalog_item) if catalog_item and commission_tax_rate == effective_vat_rate(catalog_item) else "User supplied",
            dividend_withholding_tax_rate=dividend_withholding_tax_rate,
            dividend_withholding_tax_source="Broker override" if dividend_withholding_tax_rate is not None else "Investor profile default",
            is_active=True,
        )
        self.db.add(broker)
        self.db.commit()
        self.db.refresh(broker)
        return broker

    def close(self, broker_id: int) -> dict:
        broker = self.get(broker_id)
        portfolios = (self.db.query(Portfolio).join(Entity, Portfolio.entity_id == Entity.id)
                      .filter(Portfolio.broker_id == broker.id, Entity.user_id == self.user_id, Portfolio.is_active.is_(True))
                      .with_for_update().all())
        portfolio_ids = [item.id for item in portfolios]
        positions = [] if not portfolio_ids else (self.db.query(Position, Security)
                    .join(Security, Security.id == Position.security_id)
                    .filter(Position.portfolio_id.in_(portfolio_ids), Position.quantity > 0).all())
        credits: dict[int, Decimal] = {}
        total_written_off = Decimal("0")
        resolver = InvestmentAccountResolver(self.db)
        for position, security in positions:
            book_value = position.quantity * position.average_cost
            if book_value > 0:
                account = resolver.resolve(security)
                credits[account.id] = credits.get(account.id, Decimal("0")) + book_value
                total_written_off += book_value
            position.quantity = Decimal("0")
            position.average_cost = Decimal("0")
            position.next_distribution_date = None
            position.expected_distribution_amount = None
            position.distribution_frequency = None
            position.fair_value = None
        portfolio_cash = sum((item.cash_balance for item in portfolios), Decimal("0"))
        if portfolio_cash > 0:
            cash_account = resolver.get_brokerage_cash_account()
            credits[cash_account.id] = credits.get(cash_account.id, Decimal("0")) + portfolio_cash
            total_written_off += portfolio_cash
        if total_written_off > 0:
            loss_account = AccountResolver(self.db).get_realized_loss_account()
            lines = [JournalLineInput(account_id=loss_account.id, debit=total_written_off, credit=Decimal("0"))]
            lines.extend(JournalLineInput(account_id=account_id, debit=Decimal("0"), credit=value) for account_id, value in credits.items())
            LedgerService(self.db).post(user_id=self.user_id, description=f"Broker closure write-off · {broker.name}", lines=lines, related_reference=f"broker-closure:{broker.id}")
        for portfolio in portfolios:
            portfolio.cash_balance = Decimal("0")
            portfolio.is_active = False
        broker.is_active = False
        self.db.commit()
        return {"broker_id": broker.id, "portfolios_closed": len(portfolios), "positions_closed": len(positions), "value_written_off": total_written_off}
