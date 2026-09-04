from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.schemas.journal import JournalLineInput
from app.accounting.services.investment_account_resolver import (
    InvestmentAccountResolver,
)
from app.accounting.services.ledger_service import LedgerService
from app.investing.enums.trade_type import TradeType
from app.investing.repositories.security_repository import (
    SecurityRepository,
)
from app.investing.repositories.trade_repository import TradeRepository
from app.investing.services.position_service import PositionService
from app.investing.models.portfolio import Portfolio


class BuyStockService:
    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.trade_repository = TradeRepository(db)
        self.position_service = PositionService(db)
        self.security_repository = SecurityRepository(db)
        self.ledger = LedgerService(db)
        self.user_id = user_id
        self.investment_account_resolver = (
            InvestmentAccountResolver(db)
        )

    def buy(
        self,
        portfolio_id: int,
        broker_id: int,
        security_id: int,
        quantity: Decimal,
        price: Decimal,
        commission: Decimal,
        trade_date: datetime,
    ):
        security = self.security_repository.get(
            security_id,
        )

        if security is None:
            raise ValueError(
                f"Security with id {security_id} not found."
            )

        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).with_for_update().one()
        if security.currency_code != portfolio.base_currency.code:
            raise ValueError(
                f"{security.name} trades in {security.currency_code} and cannot be added to a {portfolio.base_currency.code} portfolio. Select a compatible portfolio."
            )

        trade = self.trade_repository.create_trade(
            portfolio_id=portfolio_id,
            broker_id=broker_id,
            security_id=security_id,
            side=TradeType.BUY,
            quantity=quantity,
            price=price,
            commission=commission,
            trade_date=trade_date,
        )

        total_cost = (quantity * price) + commission

        if portfolio.cash_balance < total_cost:
            raise ValueError(
                f"Insufficient portfolio cash. Available: {portfolio.cash_balance:.2f}; required: {total_cost:.2f}. Fund the portfolio before buying."
            )
        portfolio.cash_balance -= total_cost

        unit_cost = total_cost / quantity

        position = self.position_service.update_buy(
            portfolio_id=portfolio_id,
            security_id=security_id,
            quantity=quantity,
            price=unit_cost,
        )

        investment_account = (
            self.investment_account_resolver.resolve(
                security,
            )
        )

        cash_account = (
            self.investment_account_resolver
            .get_brokerage_cash_account()
        )

        display_name = security.name.removesuffix(" Fund") if security.security_type == "REIT" else security.name
        entry = self.ledger.post(
            user_id=self.user_id,
            description=f"Buy · {display_name} · {format(quantity.normalize(), 'f')} Units",
            transaction_date=trade_date,
            lines=[
                JournalLineInput(
                    account_id=investment_account.id,
                    debit=total_cost,
                    credit=Decimal("0.00"),
                ),
                JournalLineInput(
                    account_id=cash_account.id,
                    debit=Decimal("0.00"),
                    credit=total_cost,
                ),
            ],
            related_reference=f"portfolio:{portfolio_id}:security:{security_id}",
        )

        self.db.commit()

        self.db.refresh(trade)
        self.db.refresh(position)
        self.db.refresh(entry)

        return {
            "trade": trade,
            "position": position,
            "journal_entry": entry,
        }
