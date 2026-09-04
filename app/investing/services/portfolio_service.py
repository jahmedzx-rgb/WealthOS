from sqlalchemy.orm import Session

from app.investing.models.portfolio import Portfolio
from app.investing.models.portfolio_strategy import PortfolioStrategy
from app.investing.models.portfolio_objective import PortfolioObjective
from app.core.models.entity import Entity
from app.core.models.currency import Currency
from uuid import uuid4


class PortfolioService:
    def __init__(self, db: Session):
        self.db = db

    def get(self, portfolio_id: int, user_id: int | None = None) -> Portfolio:
        query = self.db.query(Portfolio).join(Entity, Portfolio.entity_id == Entity.id).filter(Portfolio.id == portfolio_id)
        if user_id is not None:
            query = query.filter(Entity.user_id == user_id)
        portfolio = (
            query.first()
        )

        if portfolio is None:
            raise ValueError(
                f"Portfolio {portfolio_id} not found."
            )

        return portfolio

    def list(self, user_id: int | None = None) -> list[Portfolio]:
        query = self.db.query(Portfolio).join(Entity, Portfolio.entity_id == Entity.id).filter(Portfolio.is_active.is_(True))
        if user_id is not None:
            query = query.filter(Entity.user_id == user_id)
        return query.order_by(Portfolio.name).all()

    def create(self, *, user_id: int, name: str, broker_id: int, portfolio_number: str, iban: str | None = None, description: str | None = None, currency_code: str | None = None) -> Portfolio:
        clean_name = name.strip()
        if len(clean_name) < 2:
            raise ValueError("Portfolio name must contain at least 2 characters.")
        entity = self.db.query(Entity).filter(Entity.user_id == user_id, Entity.is_active.is_(True)).order_by(Entity.id).first()
        if entity is None:
            raise ValueError("Complete your profile before creating a portfolio.")
        from app.investing.models.broker import Broker
        broker = self.db.query(Broker).filter(Broker.id == broker_id, Broker.user_id == user_id, Broker.is_active.is_(True)).first()
        if broker is None:
            raise ValueError("Select a registered broker before creating a portfolio.")
        duplicate = self.db.query(Portfolio).join(Entity, Portfolio.entity_id == Entity.id).filter(Entity.user_id == user_id, Portfolio.name.ilike(clean_name)).first()
        if duplicate is not None:
            raise ValueError("A portfolio with this name already exists.")
        normalized_number = "".join(portfolio_number.split()).upper()
        if len(normalized_number) < 2:
            raise ValueError("Portfolio number is required and must contain at least 2 characters.")
        number_duplicate = self.db.query(Portfolio).join(Entity, Portfolio.entity_id == Entity.id).filter(Entity.user_id == user_id, Portfolio.portfolio_number == normalized_number).first()
        if number_duplicate is not None:
            raise ValueError("This portfolio number is already registered.")
        normalized_iban = "".join((iban or "").split()).upper()
        if normalized_iban and len(normalized_iban) < 4:
            raise ValueError("IBAN must contain at least 4 characters when provided.")
        if normalized_iban:
            identifier_duplicate = self.db.query(Portfolio).join(Entity, Portfolio.entity_id == Entity.id).filter(Entity.user_id == user_id, Portfolio.account_identifier == normalized_iban).first()
            if identifier_duplicate is not None:
                raise ValueError("This IBAN is already registered.")
        strategy = self.db.query(PortfolioStrategy).filter(PortfolioStrategy.is_active.is_(True)).order_by(PortfolioStrategy.id).first()
        objective = self.db.query(PortfolioObjective).filter(PortfolioObjective.is_active.is_(True)).order_by(PortfolioObjective.id).first()
        if strategy is None or objective is None:
            raise ValueError("Portfolio reference data is unavailable.")
        currency = None
        if currency_code:
            currency = self.db.query(Currency).filter(Currency.code == currency_code.upper(), Currency.is_active.is_(True)).first()
            if currency is None:
                raise ValueError("Select a supported portfolio currency.")
        portfolio = Portfolio(
            code=f"PORT-{uuid4().hex[:10].upper()}",
            name=clean_name,
            portfolio_number=normalized_number,
            account_identifier=normalized_iban or None,
            entity_id=entity.id,
            broker_id=broker.id,
            strategy_id=strategy.id,
            objective_id=objective.id,
            base_currency_id=currency.id if currency else entity.base_currency_id,
            description=description.strip() if description else None,
            is_active=True,
        )
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio

    def update(self, *, user_id: int, portfolio_id: int, name: str, portfolio_number: str | None, iban: str | None, currency_code: str) -> Portfolio:
        portfolio = self.get(portfolio_id, user_id)
        clean_name = name.strip()
        duplicate = self.db.query(Portfolio).join(Entity, Portfolio.entity_id == Entity.id).filter(Entity.user_id == user_id, Portfolio.id != portfolio.id, Portfolio.name.ilike(clean_name)).first()
        if duplicate is not None:
            raise ValueError("A portfolio with this name already exists.")
        if portfolio_number is not None:
            normalized_number = "".join(portfolio_number.split()).upper()
            number_duplicate = self.db.query(Portfolio).join(Entity, Portfolio.entity_id == Entity.id).filter(Entity.user_id == user_id, Portfolio.id != portfolio.id, Portfolio.portfolio_number == normalized_number).first()
            if number_duplicate is not None:
                raise ValueError("This portfolio number is already registered.")
            portfolio.portfolio_number = normalized_number
        if iban is not None:
            normalized_iban = "".join(iban.split()).upper()
            identifier_duplicate = self.db.query(Portfolio).join(Entity, Portfolio.entity_id == Entity.id).filter(Entity.user_id == user_id, Portfolio.id != portfolio.id, Portfolio.account_identifier == normalized_iban).first() if normalized_iban else None
            if identifier_duplicate is not None:
                raise ValueError("This IBAN is already registered.")
            portfolio.account_identifier = normalized_iban or None
        currency = self.db.query(Currency).filter(Currency.code == currency_code.upper(), Currency.is_active.is_(True)).first()
        if currency is None:
            raise ValueError("Select a supported portfolio currency.")
        if currency.id != portfolio.base_currency_id:
            from app.investing.models.trade import Trade
            if portfolio.cash_balance != 0 or self.db.query(Trade.id).filter(Trade.portfolio_id == portfolio.id).first() is not None:
                raise ValueError("Settle portfolio cash and positions before changing its currency.")
            portfolio.base_currency_id = currency.id
        portfolio.name = clean_name
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio
