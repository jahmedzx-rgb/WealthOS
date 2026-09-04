from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from time import monotonic, sleep
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class MarketQuote:
    price: Decimal
    price_date: datetime


class MarketPriceProviderError(RuntimeError):
    pass


class MarketPriceProvider(Protocol):
    def get_latest(self, symbol: str) -> MarketQuote:
        ...


class YahooMarketPriceProvider:
    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds

    def get_latest(self, symbol: str) -> MarketQuote:
        normalized_symbol = _normalize_symbol(symbol)
        query = urlencode(
            {
                "interval": "1d",
                "range": "1d",
            }
        )

        payload = _load_json(
            url=f"{self.BASE_URL}/{normalized_symbol}?{query}",
            timeout_seconds=self.timeout_seconds,
            symbol=normalized_symbol,
        )

        try:
            chart = payload["chart"]
            provider_error = chart.get("error")

            if provider_error:
                description = (
                    provider_error.get("description")
                    or provider_error.get("code")
                    or "Unknown provider error."
                )
                raise MarketPriceProviderError(
                    f"Provider rejected {normalized_symbol}: "
                    f"{description}"
                )

            result = chart["result"][0]
            metadata = result["meta"]
            price = Decimal(str(metadata["regularMarketPrice"]))
            price_date = datetime.fromtimestamp(
                int(metadata["regularMarketTime"]),
                tz=timezone.utc,
            ).replace(tzinfo=None)
        except MarketPriceProviderError:
            raise
        except (
            IndexError,
            KeyError,
            TypeError,
            InvalidOperation,
            ValueError,
        ) as error:
            raise MarketPriceProviderError(
                "Provider returned an invalid quote for "
                f"{normalized_symbol}."
            ) from error

        _validate_price(price, normalized_symbol)

        return MarketQuote(
            price=price,
            price_date=price_date,
        )


class AlphaVantageMarketPriceProvider:
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(
        self,
        api_key: str,
        timeout_seconds: float = 10.0,
        request_interval_seconds: float = 1.1,
    ):
        if not api_key:
            raise ValueError(
                "ALPHA_VANTAGE_API_KEY is not configured."
            )

        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.request_interval_seconds = request_interval_seconds
        self._last_request_started_at: float | None = None

    def get_latest(self, symbol: str) -> MarketQuote:
        normalized_symbol = _normalize_symbol(symbol)
        self._wait_for_rate_limit()

        query = urlencode(
            {
                "function": "GLOBAL_QUOTE",
                "symbol": normalized_symbol,
                "apikey": self.api_key,
            }
        )

        payload = _load_json(
            url=f"{self.BASE_URL}?{query}",
            timeout_seconds=self.timeout_seconds,
            symbol=normalized_symbol,
        )

        if not isinstance(payload, dict):
            raise MarketPriceProviderError(
                "Provider returned an invalid response for "
                f"{normalized_symbol}."
            )

        error_message = (
            payload.get("Error Message")
            or payload.get("Note")
            or payload.get("Information")
        )

        if error_message:
            raise MarketPriceProviderError(
                f"Provider rejected {normalized_symbol}: "
                f"{error_message}"
            )

        quote = payload.get("Global Quote") or {}

        try:
            price = Decimal(quote["05. price"])
            price_date = datetime.strptime(
                quote["07. latest trading day"],
                "%Y-%m-%d",
            )
        except (KeyError, InvalidOperation, ValueError) as error:
            raise MarketPriceProviderError(
                "Provider returned an invalid quote for "
                f"{normalized_symbol}."
            ) from error

        _validate_price(price, normalized_symbol)

        return MarketQuote(
            price=price,
            price_date=price_date,
        )

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_started_at is not None:
            elapsed = monotonic() - self._last_request_started_at
            remaining = self.request_interval_seconds - elapsed

            if remaining > 0:
                sleep(remaining)

        self._last_request_started_at = monotonic()


class FallbackMarketPriceProvider:
    def __init__(
        self,
        primary: MarketPriceProvider,
        fallback: MarketPriceProvider,
    ):
        self.primary = primary
        self.fallback = fallback

    def get_latest(self, symbol: str) -> MarketQuote:
        try:
            return self.primary.get_latest(symbol)
        except MarketPriceProviderError as primary_error:
            try:
                return self.fallback.get_latest(symbol)
            except MarketPriceProviderError as fallback_error:
                raise MarketPriceProviderError(
                    f"All market price providers failed for {symbol}."
                ) from ExceptionGroup(
                    "Market price provider failures",
                    [primary_error, fallback_error],
                )


def create_market_price_provider(
    provider_name: str,
    fallback_provider_name: str | None,
    alpha_vantage_api_key: str | None,
    timeout_seconds: float,
    request_interval_seconds: float,
) -> MarketPriceProvider:
    primary_name = provider_name.strip().lower()
    fallback_name = (
        fallback_provider_name.strip().lower()
        if fallback_provider_name
        else None
    )

    primary = _create_named_provider(
        provider_name=primary_name,
        alpha_vantage_api_key=alpha_vantage_api_key,
        timeout_seconds=timeout_seconds,
        request_interval_seconds=request_interval_seconds,
    )

    if fallback_name is None:
        return primary

    if fallback_name == primary_name:
        raise ValueError(
            "Market price primary and fallback providers must differ."
        )

    fallback = _create_named_provider(
        provider_name=fallback_name,
        alpha_vantage_api_key=alpha_vantage_api_key,
        timeout_seconds=timeout_seconds,
        request_interval_seconds=request_interval_seconds,
    )

    return FallbackMarketPriceProvider(
        primary=primary,
        fallback=fallback,
    )


def _create_named_provider(
    provider_name: str,
    alpha_vantage_api_key: str | None,
    timeout_seconds: float,
    request_interval_seconds: float,
) -> MarketPriceProvider:
    if provider_name == "yahoo":
        return YahooMarketPriceProvider(
            timeout_seconds=timeout_seconds,
        )

    if provider_name == "alpha_vantage":
        return AlphaVantageMarketPriceProvider(
            api_key=alpha_vantage_api_key or "",
            timeout_seconds=timeout_seconds,
            request_interval_seconds=request_interval_seconds,
        )

    raise ValueError(
        f"Unsupported market price provider: {provider_name}."
    )


def _load_json(
    url: str,
    timeout_seconds: float,
    symbol: str,
) -> dict:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "WealthOS/0.1",
        },
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except (
        HTTPError,
        URLError,
        TimeoutError,
        json.JSONDecodeError,
    ) as error:
        raise MarketPriceProviderError(
            f"Could not fetch market price for {symbol}."
        ) from error

    if not isinstance(payload, dict):
        raise MarketPriceProviderError(
            f"Provider returned an invalid response for {symbol}."
        )

    return payload


def _normalize_symbol(symbol: str) -> str:
    normalized_symbol = symbol.strip().upper()

    if not normalized_symbol:
        raise ValueError("Market symbol must not be empty.")

    return normalized_symbol


def _validate_price(price: Decimal, symbol: str) -> None:
    if price <= Decimal("0"):
        raise MarketPriceProviderError(
            f"Provider returned a non-positive price for {symbol}."
        )
