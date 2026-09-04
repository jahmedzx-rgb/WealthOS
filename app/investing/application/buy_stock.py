from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.investing.application.buy_stock_service import (
    BuyStockService,
)


class BuyStockUseCase:
    def __init__(self, db: Session, user_id: int = 1):
        self.buy_stock_service = BuyStockService(db, user_id)

    def execute(
        self,
        portfolio_id: int,
        broker_id: int,
        security_id: int,
        quantity: Decimal,
        price: Decimal,
        commission: Decimal,
        trade_date: datetime,
    ):
        return self.buy_stock_service.buy(
            portfolio_id=portfolio_id,
            broker_id=broker_id,
            security_id=security_id,
            quantity=quantity,
            price=price,
            commission=commission,
            trade_date=trade_date,
        )
