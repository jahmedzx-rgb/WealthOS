from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.investing.models.trade import Trade


class TradeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_trade(
        self,
        portfolio_id: int,
        broker_id: int,
        security_id: int,
        side: str,
        quantity: Decimal,
        price: Decimal,
        commission: Decimal,
        trade_date: datetime,
    ) -> Trade:

        trade = Trade(
            portfolio_id=portfolio_id,
            broker_id=broker_id,
            security_id=security_id,
            side=side,
            quantity=quantity,
            price=price,
            commission=commission,
            trade_date=trade_date,
        )

        self.db.add(trade)

        return trade

    def list_by_position(
        self,
        portfolio_id: int,
        security_id: int,
    ):
        return (
            self.db.query(Trade)
            .filter(
                Trade.portfolio_id == portfolio_id,
                Trade.security_id == security_id,
            )
            .order_by(Trade.trade_date.desc(), Trade.id.desc())
            .all()
        )
