from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.investing.application.sell_stock_service import (
    SellStockService,
)


class SellStockUseCase:
    def __init__(self, db: Session, user_id: int = 1):
        self.sell_stock_service = SellStockService(db, user_id)

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
        return self.sell_stock_service.sell(
            portfolio_id=portfolio_id,
            broker_id=broker_id,
            security_id=security_id,
            quantity=quantity,
            price=price,
            commission=commission,
            trade_date=trade_date,
        )
