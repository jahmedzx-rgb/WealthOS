from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.investing.models.market_price import MarketPrice
from app.investing.repositories.market_price_repository import (
    MarketPriceRepository,
)


class MarketPriceService:
    def __init__(self, db: Session):
        self.market_price_repository = MarketPriceRepository(db)

    def record(
        self,
        security_id: int,
        price: Decimal,
        price_date: datetime,
    ) -> MarketPrice:
        if price <= Decimal("0"):
            raise ValueError(
                "Market price must be greater than zero."
            )

        market_price = self.market_price_repository.get_by_date(
            security_id=security_id,
            price_date=price_date,
        )

        if market_price is not None:
            market_price.price = price
            return market_price

        return self.market_price_repository.add(
            security_id=security_id,
            price=price,
            price_date=price_date,
        )

    def get_latest(
        self,
        security_id: int,
    ) -> MarketPrice:
        market_price = (
            self.market_price_repository.get_latest(
                security_id
            )
        )

        if market_price is None:
            raise ValueError(
                "Market price not found for "
                f"security {security_id}."
            )

        return market_price
