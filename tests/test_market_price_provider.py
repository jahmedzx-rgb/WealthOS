from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.investing.services import market_price_provider
from app.investing.services.market_price_provider import (
    FallbackMarketPriceProvider,
    MarketPriceProviderError,
    MarketQuote,
    YahooMarketPriceProvider,
    create_market_price_provider,
)


def test_yahoo_provider_returns_latest_quote(monkeypatch):
    monkeypatch.setattr(
        market_price_provider,
        "_load_json",
        Mock(
            return_value={
                "chart": {
                    "error": None,
                    "result": [
                        {
                            "meta": {
                                "regularMarketPrice": 231.45,
                                "regularMarketTime": 1785945600,
                            }
                        }
                    ],
                }
            }
        ),
    )

    quote = YahooMarketPriceProvider().get_latest(" aapl ")

    assert quote == MarketQuote(
        price=Decimal("231.45"),
        price_date=datetime(2026, 8, 5, 16, 0),
    )


def test_fallback_provider_does_not_call_fallback_when_primary_succeeds():
    quote = MarketQuote(
        price=Decimal("231.45"),
        price_date=datetime(2026, 8, 5),
    )
    primary = Mock()
    fallback = Mock()
    primary.get_latest.return_value = quote
    provider = FallbackMarketPriceProvider(primary, fallback)

    assert provider.get_latest("AAPL") == quote
    fallback.get_latest.assert_not_called()


def test_fallback_provider_uses_fallback_when_primary_fails():
    quote = MarketQuote(
        price=Decimal("231.45"),
        price_date=datetime(2026, 8, 5),
    )
    primary = Mock()
    fallback = Mock()
    primary.get_latest.side_effect = MarketPriceProviderError(
        "primary failed"
    )
    fallback.get_latest.return_value = quote
    provider = FallbackMarketPriceProvider(primary, fallback)

    assert provider.get_latest("AAPL") == quote
    fallback.get_latest.assert_called_once_with("AAPL")


def test_factory_creates_yahoo_without_fallback():
    provider = create_market_price_provider(
        provider_name="yahoo",
        fallback_provider_name=None,
        alpha_vantage_api_key=None,
        timeout_seconds=10.0,
        request_interval_seconds=1.1,
    )

    assert isinstance(provider, YahooMarketPriceProvider)


def test_factory_requires_key_when_alpha_is_configured_as_fallback():
    with pytest.raises(
        ValueError,
        match="ALPHA_VANTAGE_API_KEY is not configured",
    ):
        create_market_price_provider(
            provider_name="yahoo",
            fallback_provider_name="alpha_vantage",
            alpha_vantage_api_key=None,
            timeout_seconds=10.0,
            request_interval_seconds=1.1,
        )
