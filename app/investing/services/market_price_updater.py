from sqlalchemy.orm import Session

from app.investing.models.market_price import MarketPrice
from app.investing.models.security import Security
from app.investing.repositories.security_repository import (
    SecurityRepository,
)
from app.investing.services.market_price_provider import (
    MarketPriceProvider,
)
from app.investing.services.market_price_service import (
    MarketPriceService,
)

class MarketPriceUpdater:
    def __init__(
        self,
        db: Session,
        provider: MarketPriceProvider,
    ):
        self.db = db
        self.provider = provider
        self.security_repository = SecurityRepository(db)
        self.market_price_service = MarketPriceService(db)

    def update_security(
        self,
        security_id: int,
    ) -> MarketPrice:
        security = self.security_repository.get(security_id)

        if security is None:
            raise ValueError(
                f"Security {security_id} not found."
            )

        if not security.is_active:
            raise ValueError(
                f"Security {security.symbol} is inactive."
            )

        try:
            market_price = self._record_quote(security)
            self.db.commit()
            self.db.refresh(market_price)
        except Exception:
            self.db.rollback()
            raise

        return market_price

    def update_all(self) -> list[MarketPrice]:
        securities = [
            security
            for security in self.security_repository.list()
            if security.is_active
        ]

        try:
            market_prices = [
                self._record_quote(security)
                for security in securities
            ]
            self.db.commit()

            for market_price in market_prices:
                self.db.refresh(market_price)
        except Exception:
            self.db.rollback()
            raise

        return market_prices

    def _record_quote(
        self,
        security: Security,
    ) -> MarketPrice:
        quote = self.provider.get_latest(
            getattr(security, "market_symbol", None) or security.symbol
        )

        return self.market_price_service.record(
            security_id=security.id,
            price=quote.price,
            price_date=quote.price_date,
        )
