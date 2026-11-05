from io import BytesIO
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest

from app.investing.services import market_price_provider
from app.investing.services.market_price_provider import (
    AlphaVantageMarketPriceProvider,
    FallbackMarketPriceProvider,
    MarketPriceProviderError,
    MarketQuote,
    MarketPriceProviderRouter,
    SahmkMarketPriceProvider,
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


def test_yahoo_provider_returns_last_trading_close_in_requested_month(monkeypatch):
    close_dates = [datetime(2026, 9, day, 20, tzinfo=timezone.utc) for day in (29, 30)]
    monkeypatch.setattr(
        market_price_provider,
        "_load_json",
        Mock(return_value={"chart": {"error": None, "result": [{
            "meta": {"exchangeTimezoneName": "America/New_York"},
            "timestamp": [int(item.timestamp()) for item in close_dates],
            "indicators": {"quote": [{"close": [42.5, 43.25]}]},
        }]}}),
    )

    quote = YahooMarketPriceProvider().get_historical_close("AAPL", date(2026, 9, 30))

    assert quote == MarketQuote(Decimal("43.25"), datetime(2026, 9, 30, 23, 59, 59))


def test_yahoo_provider_does_not_substitute_a_previous_month_close(monkeypatch):
    monkeypatch.setattr(
        market_price_provider,
        "_load_json",
        Mock(return_value={"chart": {"error": None, "result": [{
            "meta": {"exchangeTimezoneName": "America/New_York"},
            "timestamp": [int(datetime(2026, 8, 31, 20, tzinfo=timezone.utc).timestamp())],
            "indicators": {"quote": [{"close": [42.5]}]},
        }]}}),
    )

    with pytest.raises(MarketPriceProviderError, match="No historical close"):
        YahooMarketPriceProvider().get_historical_close("AAPL", date(2026, 9, 30))


def test_yahoo_request_retries_rate_limit_responses(monkeypatch):
    response = BytesIO(b'{"chart":{"error":null,"result":[]}}')
    request = Mock(side_effect=[HTTPError("https://example.test", 429, "Too Many Requests", {}, None), response])
    monkeypatch.setattr(market_price_provider, "urlopen", request)
    monkeypatch.setattr(market_price_provider, "sleep", Mock())

    assert market_price_provider._load_json("https://example.test", 1, "AAPL") == {"chart": {"error": None, "result": []}}
    assert request.call_count == 2


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


def test_alpha_vantage_provider_does_not_expose_remote_error_or_api_key(monkeypatch):
    provider = AlphaVantageMarketPriceProvider(
        api_key="private-test-key",
        timeout_seconds=1.0,
        request_interval_seconds=0,
    )
    monkeypatch.setattr(
        market_price_provider,
        "_load_json",
        lambda **_kwargs: {
            "Information": "Limit reached for key private-test-key"
        },
    )

    with pytest.raises(MarketPriceProviderError) as error:
        provider.get_latest("AAPL")

    assert "private-test-key" not in str(error.value)
    assert "Limit reached" not in str(error.value)


def test_sahmk_provider_fetches_saudi_quote_with_documented_auth_header(monkeypatch):
    request = Mock(return_value={
        "symbol": "4002",
        "price": 132.5,
        "updated_at": "2026-10-29T12:20:00+03:00",
        "is_delayed": True,
    })
    monkeypatch.setattr(market_price_provider, "_load_json", request)
    provider = SahmkMarketPriceProvider("private-test-key")

    quote = provider.get_latest("4002.SR")

    assert quote == MarketQuote(Decimal("132.5"), datetime(2026, 10, 29, 9, 20))
    request.assert_called_once_with(
        "https://api.sahmk.sa/api/v1/quote/4002/",
        10.0,
        "4002.SR",
        headers={"X-API-Key": "private-test-key"},
    )


def test_sahmk_provider_reuses_quote_across_instances_within_cache_window(monkeypatch):
    SahmkMarketPriceProvider._quote_cache.clear()
    request = Mock(return_value={
        "symbol": "4336",
        "price": 8.25,
        "updated_at": "2026-10-29T12:20:00+00:00",
    })
    monkeypatch.setattr(market_price_provider, "_load_json", request)
    provider = SahmkMarketPriceProvider("private-test-key")
    second_provider = SahmkMarketPriceProvider("private-test-key")

    first = provider.get_latest("4336.SR")
    second = second_provider.get_latest("4336")

    assert first == second
    assert SahmkMarketPriceProvider.CACHE_TTL_SECONDS == 40 * 60
    request.assert_called_once()
    SahmkMarketPriceProvider._quote_cache.clear()


def test_market_price_router_uses_sahmk_for_saudi_and_default_for_us():
    default = Mock()
    saudi = Mock()
    expected = MarketQuote(Decimal("50"), datetime(2026, 10, 29))
    default.get_latest.return_value = expected
    saudi.get_latest.return_value = expected
    router = MarketPriceProviderRouter(default, saudi)

    assert router.get_latest("4002.SR") == expected
    assert router.get_latest("AAPL") == expected
    saudi.get_latest.assert_called_once_with("4002.SR")
    default.get_latest.assert_called_once_with("AAPL")
