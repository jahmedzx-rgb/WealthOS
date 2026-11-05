from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session

from app.investing.models.market_price import MarketPrice
from app.investing.models.security import Security
from app.investing.repositories.security_repository import (
    SecurityRepository,
)
from app.investing.services.market_price_provider import (
    MarketPriceProvider,
    YahooMarketPriceProvider,
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
        self.last_failure_messages: dict[int, str] = {}

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
            for security in self.security_repository.list_active_held()
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

    def update_securities(self, security_ids: list[int]) -> tuple[list[MarketPrice], list[int]]:
        requested_ids = set(security_ids)
        if not requested_ids:
            return [], []

        self.last_failure_messages = {}

        securities = self.security_repository.list_active_by_ids(requested_ids)
        if not securities:
            self.last_failure_messages = {security_id: "Security is inactive or unavailable." for security_id in requested_ids}
            return [], sorted(requested_ids)

        quotes = {}
        failed_ids = set(requested_ids) - {security.id for security in securities}

        def fetch(security: Security):
            symbol = getattr(security, "market_symbol", None) or security.symbol
            option_fetcher = getattr(self.provider, "get_option_latest", None)
            if getattr(security, "security_type", None) == "OPTION" and option_fetcher is not None:
                quote = option_fetcher(symbol)
            else:
                quote = self.provider.get_latest(symbol)
            return security.id, quote

        if isinstance(self.provider, YahooMarketPriceProvider) and len(securities) > 1:
            with ThreadPoolExecutor(max_workers=min(5, len(securities))) as executor:
                futures = {executor.submit(fetch, security): security.id for security in securities}
                for future in as_completed(futures):
                    security_id = futures[future]
                    try:
                        _security_id, quotes[security_id] = future.result()
                    except Exception as error:
                        failed_ids.add(security_id)
                        self.last_failure_messages[security_id] = str(error)
        else:
            for security in securities:
                try:
                    _security_id, quotes[security.id] = fetch(security)
                except Exception as error:
                    failed_ids.add(security.id)
                    self.last_failure_messages[security.id] = str(error)

        for security_id in requested_ids - {security.id for security in securities}:
            self.last_failure_messages[security_id] = "Security is inactive or unavailable."

        updated = []
        try:
            for security in securities:
                quote = quotes.get(security.id)
                if quote is None:
                    continue
                updated.append(self.market_price_service.record(
                    security_id=security.id,
                    price=quote.price,
                    price_date=quote.price_date,
                ))
            if updated:
                self.db.commit()
                for market_price in updated:
                    self.db.refresh(market_price)
        except Exception:
            self.db.rollback()
            raise

        return updated, sorted(failed_ids)

    def _record_quote(
        self,
        security: Security,
    ) -> MarketPrice:
        symbol = getattr(security, "market_symbol", None) or security.symbol
        option_fetcher = getattr(self.provider, "get_option_latest", None)
        quote = option_fetcher(symbol) if getattr(security, "security_type", None) == "OPTION" and option_fetcher is not None else self.provider.get_latest(symbol)

        return self.market_price_service.record(
            security_id=security.id,
            price=quote.price,
            price_date=quote.price_date,
        )
