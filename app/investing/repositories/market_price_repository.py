from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.investing.models.market_price import MarketPrice


class MarketPriceRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(
        self,
        security_id: int,
        price: Decimal,
        price_date: datetime,
    ) -> MarketPrice:
        market_price = MarketPrice(
            security_id=security_id,
            price=price,
            price_date=price_date,
        )

        self.db.add(market_price)

        return market_price

    def get_latest(
        self,
        security_id: int,
    ) -> MarketPrice | None:
        return (
            self.db.query(MarketPrice)
            .filter(
                MarketPrice.security_id == security_id,
            )
            .order_by(
                MarketPrice.price_date.desc(),
                MarketPrice.id.desc(),
            )
            .first()
        )

    def get_by_date(
        self,
        security_id: int,
        price_date: datetime,
    ) -> MarketPrice | None:
        return (
            self.db.query(MarketPrice)
            .filter(
                MarketPrice.security_id == security_id,
                MarketPrice.price_date == price_date,
            )
            .first()
        )
