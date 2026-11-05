from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from http.cookiejar import CookieJar
import json
import re
from threading import Lock
from time import monotonic, sleep
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen


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
    OPTIONS_URL = "https://query1.finance.yahoo.com/v7/finance/options"

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds

    def get_latest(self, symbol: str) -> MarketQuote:
        normalized_symbol = _normalize_symbol(symbol)
        option = _parse_option_symbol(normalized_symbol)
        if option is not None:
            return self.get_option_latest(normalized_symbol, option=option)
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

    def get_option_latest(self, symbol: str, *, option=None) -> MarketQuote:
        normalized_symbol = _normalize_symbol(symbol)
        option = option or _parse_option_symbol(normalized_symbol)
        if option is None:
            raise MarketPriceProviderError(f"Could not identify option contract {normalized_symbol}.")
        underlying, expiration, option_type, strike = option
        expiry_timestamp = int(datetime.combine(expiration, time.min, tzinfo=timezone.utc).timestamp())
        query = urlencode({"date": expiry_timestamp})
        payload = _load_yahoo_options_json(
            f"{self.OPTIONS_URL}/{underlying}?{query}",
            timeout_seconds=self.timeout_seconds,
            symbol=normalized_symbol,
        )
        try:
            chain = payload["optionChain"]
            if chain.get("error"):
                detail = chain["error"].get("description") or chain["error"].get("code") or "Unknown provider error."
                raise MarketPriceProviderError(f"Provider rejected {normalized_symbol}: {detail}")
            result = chain["result"][0]
            expirations = result.get("expirationDates", [])
            if expiry_timestamp not in expirations:
                raise MarketPriceProviderError(f"Yahoo Finance has no option chain for {underlying} expiring {expiration.isoformat()}.")
            contracts = result["options"][0]["calls" if option_type == "C" else "puts"]
            contract = next((item for item in contracts if Decimal(str(item.get("strike"))) == strike), None)
            if contract is None:
                raise MarketPriceProviderError(f"Yahoo Finance did not return {normalized_symbol} in the option chain.")
            bid = Decimal(str(contract.get("bid") or 0))
            ask = Decimal(str(contract.get("ask") or 0))
            last = Decimal(str(contract.get("lastPrice") or 0))
            if bid > 0 and ask > 0:
                price = (bid + ask) / Decimal("2")
                # Yahoo does not provide a quote timestamp for the bid/ask fields.
                # Mark the chain snapshot time rather than reusing an old last-trade date.
                price_date = datetime.now(timezone.utc).replace(tzinfo=None)
            elif last > 0 and contract.get("lastTradeDate"):
                price = last
                price_date = datetime.fromtimestamp(int(contract["lastTradeDate"]), tz=timezone.utc).replace(tzinfo=None)
            else:
                raise MarketPriceProviderError(f"Yahoo Finance returned no usable bid, ask, or recent trade for {normalized_symbol}.")
        except MarketPriceProviderError:
            raise
        except (IndexError, KeyError, TypeError, InvalidOperation, ValueError) as error:
            raise MarketPriceProviderError(f"Yahoo Finance returned an invalid option quote for {normalized_symbol}.") from error

        _validate_price(price, normalized_symbol)
        return MarketQuote(price=price, price_date=price_date)

    def get_historical_close(self, symbol: str, on_date: date) -> MarketQuote:
        normalized_symbol = _normalize_symbol(symbol)
        # Read the whole target month so weekends and long market holidays still resolve
        # to that month's last actual trading-session close (never a prior-month quote).
        month_start = date(on_date.year, on_date.month, 1)
        start = datetime.combine(month_start - timedelta(days=5), time.min, tzinfo=timezone.utc)
        end = datetime.combine(on_date + timedelta(days=2), time.min, tzinfo=timezone.utc)
        query = urlencode({"interval": "1d", "period1": int(start.timestamp()), "period2": int(end.timestamp())})
        payload = _load_json(f"{self.BASE_URL}/{normalized_symbol}?{query}", self.timeout_seconds, normalized_symbol)
        try:
            chart = payload["chart"]
            if chart.get("error"):
                raise MarketPriceProviderError(f"Provider rejected {normalized_symbol}: {chart['error'].get('description') or chart['error'].get('code') or 'Unknown provider error.'}")
            result = chart["result"][0]
            metadata = result["meta"]
            try:
                exchange_zone = ZoneInfo(metadata.get("exchangeTimezoneName") or "UTC")
            except ZoneInfoNotFoundError:
                # Windows Python may not ship the IANA database. Yahoo includes
                # the exchange's current UTC offset in chart metadata.
                exchange_zone = timezone(timedelta(seconds=int(metadata.get("gmtoffset", 0))))
            timestamps = result["timestamp"]
            closes = result["indicators"]["quote"][0]["close"]
            daily = []
            for timestamp, close in zip(timestamps, closes):
                local_date = datetime.fromtimestamp(int(timestamp), tz=exchange_zone).date()
                if month_start <= local_date <= on_date and close is not None:
                    daily.append((local_date, Decimal(str(close))))
            if not daily:
                raise MarketPriceProviderError(f"No historical close was available for {normalized_symbol} on or before {on_date}.")
            price_date, price = max(daily, key=lambda item: item[0])
        except MarketPriceProviderError:
            raise
        except (IndexError, KeyError, TypeError, InvalidOperation, ValueError, ZoneInfoNotFoundError) as error:
            raise MarketPriceProviderError(f"Provider returned invalid historical prices for {normalized_symbol}.") from error
        _validate_price(price, normalized_symbol)
        return MarketQuote(price=price, price_date=datetime.combine(price_date, time(23, 59, 59)))


class SahmkMarketPriceProvider:
    """Saudi Exchange quotes from the SAHMK API (free tier is delayed)."""

    BASE_URL = "https://api.sahmk.sa/api/v1/quote"
    CACHE_TTL_SECONDS = 40 * 60
    _quote_cache: dict[str, tuple[float, MarketQuote]] = {}
    _cache_lock = Lock()

    def __init__(self, api_key: str, timeout_seconds: float = 10.0):
        if not api_key:
            raise ValueError("SAHMK_API_KEY is not configured.")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def get_latest(self, symbol: str) -> MarketQuote:
        normalized_symbol = _normalize_symbol(symbol)
        code = normalized_symbol.removesuffix(".SR")
        with self._cache_lock:
            cached = self._quote_cache.get(code)
            if cached and monotonic() - cached[0] < self.CACHE_TTL_SECONDS:
                return cached[1]
        payload = _load_json(
            f"{self.BASE_URL}/{code}/",
            self.timeout_seconds,
            normalized_symbol,
            headers={"X-API-Key": self.api_key},
        )
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        try:
            price = Decimal(str(data["price"]))
            raw_timestamp = str(data["updated_at"])
            price_date = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
            if price_date.tzinfo is not None:
                price_date = price_date.astimezone(timezone.utc).replace(tzinfo=None)
        except (KeyError, TypeError, InvalidOperation, ValueError) as error:
            raise MarketPriceProviderError(
                f"SAHMK returned an invalid quote for {normalized_symbol}."
            ) from error
        _validate_price(price, normalized_symbol)
        quote = MarketQuote(price=price, price_date=price_date)
        with self._cache_lock:
            self._quote_cache[code] = (monotonic(), quote)
        return quote


class MarketPriceProviderRouter:
    """Route Saudi-listed instruments to their dedicated provider."""

    def __init__(self, default: MarketPriceProvider, saudi: MarketPriceProvider):
        self.default = default
        self.saudi = saudi

    def get_latest(self, symbol: str) -> MarketQuote:
        normalized = symbol.strip().upper()
        if normalized.endswith(".SR") or re.fullmatch(r"\d{4,5}", normalized):
            return self.saudi.get_latest(normalized)
        return self.default.get_latest(normalized)

    def get_option_latest(self, symbol: str) -> MarketQuote:
        option_fetcher = getattr(self.default, "get_option_latest", None)
        if option_fetcher is None:
            raise MarketPriceProviderError(f"No configured provider supports option quotes for {symbol}.")
        return option_fetcher(symbol)


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
                f"Alpha Vantage rejected {normalized_symbol} "
                "(rate limit or provider request error)."
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

    def get_option_latest(self, symbol: str) -> MarketQuote:
        errors = []
        for provider in (self.primary, self.fallback):
            get_option = getattr(provider, "get_option_latest", None)
            if get_option is None:
                continue
            try:
                return get_option(symbol)
            except MarketPriceProviderError as error:
                errors.append(error)
        if not errors:
            raise MarketPriceProviderError(f"No configured provider supports option quotes for {symbol}.")
        raise MarketPriceProviderError(f"All configured option quote providers failed for {symbol}.") from ExceptionGroup(
            "Option quote provider failures",
            errors,
        )


def _parse_option_symbol(symbol: str) -> tuple[str, date, str, Decimal] | None:
    normalized = symbol.strip().upper()
    occ = re.fullmatch(r"([A-Z0-9.]{1,6}?)(\d{6})([CP])(\d{8})", normalized.replace(" ", ""))
    if occ:
        underlying, expiry, option_type, strike = occ.groups()
        try:
            expiration = datetime.strptime(expiry, "%y%m%d").date()
        except ValueError:
            return None
        return underlying, expiration, option_type, Decimal(strike) / Decimal("1000")

    separated = re.fullmatch(r"([A-Z][A-Z0-9.]*)-(\d{4})(\d{2})(\d{2})-([CP])(\d+(?:\.\d+)?)", normalized)
    if separated:
        underlying, year, month, day, option_type, strike = separated.groups()
        try:
            expiration = date(int(year), int(month), int(day))
        except ValueError:
            return None
        return underlying, expiration, option_type, Decimal(strike)

    compact = re.fullmatch(r"([A-Z][A-Z0-9.]*?)(\d{6})([CP])(\d+(?:\.\d+)?)", normalized)
    if compact:
        underlying, expiry, option_type, strike = compact.groups()
        try:
            expiration = datetime.strptime(expiry, "%y%m%d").date()
        except ValueError:
            return None
        return underlying, expiration, option_type, Decimal(strike)

    return None


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
    headers: dict[str, str] | None = None,
) -> dict:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "WealthOS/0.1",
            **(headers or {}),
        },
    )

    last_error = None
    for attempt in range(4):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                payload = json.load(response)
            break
        except HTTPError as error:
            last_error = error
            if error.code != 429 and not 500 <= error.code < 600:
                raise MarketPriceProviderError(
                    f"Could not fetch market price for {symbol}."
                ) from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            last_error = error
        if attempt < 3:
            sleep(0.5 * (2 ** attempt))
    else:
        raise MarketPriceProviderError(
            f"Could not fetch market price for {symbol} after retries."
        ) from last_error

    if not isinstance(payload, dict):
        raise MarketPriceProviderError(
            f"Provider returned an invalid response for {symbol}."
        )

    return payload


def _load_yahoo_options_json(url: str, *, timeout_seconds: float, symbol: str) -> dict:
    """Yahoo's option-chain endpoint requires the cookie/crumb session used by its finance site."""
    cookie_jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))
    headers = {
        "Accept": "application/json,text/plain,*/*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36",
    }
    try:
        try:
            with opener.open(Request("https://fc.yahoo.com", headers=headers), timeout=timeout_seconds):
                pass
        except HTTPError as error:
            # Yahoo commonly uses a 404 response here while still setting the session cookie.
            if error.code not in {401, 404}:
                raise
        with opener.open(Request("https://query1.finance.yahoo.com/v1/test/getcrumb", headers=headers), timeout=timeout_seconds) as response:
            crumb = response.read().decode("utf-8").strip()
        if not crumb:
            raise MarketPriceProviderError(f"Yahoo Finance did not issue an options quote session for {symbol}.")
        separator = "&" if "?" in url else "?"
        request_url = f"{url}{separator}{urlencode({'crumb': crumb})}"
        with opener.open(Request(request_url, headers=headers), timeout=timeout_seconds) as response:
            payload = json.load(response)
    except MarketPriceProviderError:
        raise
    except HTTPError as error:
        if error.code == 401:
            raise MarketPriceProviderError(f"Yahoo Finance rejected the options quote request for {symbol}.") from error
        raise MarketPriceProviderError(f"Could not fetch the Yahoo Finance option chain for {symbol} (HTTP {error.code}).") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise MarketPriceProviderError(f"Could not fetch the Yahoo Finance option chain for {symbol}.") from error
    if not isinstance(payload, dict):
        raise MarketPriceProviderError(f"Yahoo Finance returned an invalid option chain for {symbol}.")
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
