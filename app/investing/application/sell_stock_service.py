from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.schemas.journal import JournalLineInput
from app.accounting.services.investment_account_resolver import InvestmentAccountResolver
from app.accounting.services.ledger_service import LedgerService
from app.investing.enums.trade_type import TradeType
from app.investing.repositories.trade_repository import TradeRepository
from app.investing.services.position_service import PositionService
from app.investing.services.sale_calculation_service import (
    SaleCalculationService,
)
from app.investing.models.portfolio import Portfolio
from app.investing.repositories.security_repository import SecurityRepository


class SellStockService:
    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.trade_repository = TradeRepository(db)
        self.position_service = PositionService(db)
        self.sale_calculation = SaleCalculationService()
        self.ledger = LedgerService(db)
        self.user_id = user_id
        self.security_repository = SecurityRepository(db)
        self.investment_account_resolver = InvestmentAccountResolver(db)

    def sell(
        self,
        portfolio_id: int,
        broker_id: int,
        security_id: int,
        quantity: Decimal,
        price: Decimal,
        commission: Decimal,
        trade_date: datetime,
    ):
        position = self.position_service.validate_sell(
            portfolio_id=portfolio_id,
            security_id=security_id,
            quantity=quantity,
        )
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).with_for_update().one()
        security = self.security_repository.get(security_id)
        if security is None:
            raise ValueError(f"Security with id {security_id} not found.")
        if security.currency_code != portfolio.base_currency.code:
            raise ValueError(
                f"{security.name} trades in {security.currency_code} and cannot be sold through a {portfolio.base_currency.code} portfolio. Select its original compatible portfolio."
            )

        sale = self.sale_calculation.calculate(
            average_cost=position.average_cost,
            sell_quantity=quantity,
            sell_price=price,
            commission=commission,
        )
        portfolio.cash_balance += sale["net_proceeds"]

        self.position_service.update_sell(
            portfolio_id=portfolio_id,
            security_id=security_id,
            quantity=quantity,
        )

        trade = self.trade_repository.create_trade(
            portfolio_id=portfolio_id,
            broker_id=broker_id,
            security_id=security_id,
            side=TradeType.SELL,
            quantity=quantity,
            price=price,
            commission=commission,
            trade_date=trade_date,
        )

        investment_account = self.investment_account_resolver.resolve(security)

        cash_account = (
            self.investment_account_resolver.get_brokerage_cash_account()
        )
        gain_account = self.investment_account_resolver.account_resolver.get_realized_gain_account()
        loss_account = self.investment_account_resolver.account_resolver.get_realized_loss_account()
        fee_account = self.investment_account_resolver.account_resolver.get_by_code(5610)

        display_name = security.name.removesuffix(" Fund") if security.security_type == "REIT" else security.name
        gross_gain_loss = sale["gross_proceeds"] - sale["cost_basis"]
        lines = [
            JournalLineInput(account_id=cash_account.id, debit=sale["net_proceeds"], credit=Decimal("0.00")),
            JournalLineInput(account_id=investment_account.id, debit=Decimal("0.00"), credit=sale["cost_basis"]),
        ]
        if commission:
            lines.append(JournalLineInput(account_id=fee_account.id, debit=commission, credit=Decimal("0.00")))
        if gross_gain_loss > 0:
            lines.append(JournalLineInput(account_id=gain_account.id, debit=Decimal("0.00"), credit=gross_gain_loss))
        elif gross_gain_loss < 0:
            lines.append(JournalLineInput(account_id=loss_account.id, debit=-gross_gain_loss, credit=Decimal("0.00")))
        entry = self.ledger.post(
            user_id=self.user_id,
            description=f"Sell · {display_name} · {format(quantity.normalize(), 'f')} Units",
            transaction_date=trade_date,
            lines=lines,
            related_reference=f"portfolio:{portfolio_id}:security:{security_id}",
        )

        self.db.commit()

        self.db.refresh(trade)
        self.db.refresh(entry)

        return {
            "trade": trade,
            "sale": sale,
            "journal_entry": entry,
        }
