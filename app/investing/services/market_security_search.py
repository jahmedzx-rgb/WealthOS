from dataclasses import dataclass
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.investing.services.market_price_provider import MarketPriceProviderError


@dataclass(frozen=True)
class MarketSecurityResult:
    symbol: str
    market_symbol: str
    name: str
    security_type: str
    exchange: str
    currency_code: str


class YahooMarketSecuritySearch:
    URL = "https://query1.finance.yahoo.com/v1/finance/search"

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, limit: int = 8) -> list[MarketSecurityResult]:
        normalized = query.strip()
        if len(normalized) < 2:
            return []
        request = Request(
            f"{self.URL}?{urlencode({'q': normalized, 'quotesCount': limit, 'newsCount': 0})}",
            headers={"Accept": "application/json", "User-Agent": "WealthOS/0.1"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise MarketPriceProviderError("Could not search market securities.") from error

        results: list[MarketSecurityResult] = []
        for item in payload.get("quotes", []):
            quote_type = str(item.get("quoteType", "")).upper()
            if quote_type not in {"EQUITY", "ETF"}:
                continue
            market_symbol = str(item.get("symbol", "")).upper().strip()
            name = str(item.get("longname") or item.get("shortname") or market_symbol).strip()
            if not market_symbol or not name:
                continue
            is_saudi = market_symbol.endswith(".SR")
            symbol = market_symbol[:-3] if is_saudi else market_symbol
            exchange = "SAUDI_EXCHANGE" if is_saudi else _exchange_name(str(item.get("exchange") or item.get("exchDisp") or "GLOBAL"))
            currency = "SAR" if is_saudi else str(item.get("currency") or "").upper()
            results.append(MarketSecurityResult(symbol=symbol, market_symbol=market_symbol, name=name, security_type="ETF" if quote_type == "ETF" else "STOCK", exchange=exchange, currency_code=currency))
        return results

    def resolve(self, market_symbol: str) -> MarketSecurityResult:
        request = Request(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{market_symbol}?{urlencode({'interval': '1d', 'range': '1d'})}",
            headers={"Accept": "application/json", "User-Agent": "WealthOS/0.1"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                metadata = json.load(response)["chart"]["result"][0]["meta"]
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
            raise MarketPriceProviderError(f"Could not verify market security {market_symbol}.") from error
        normalized = market_symbol.upper().strip()
        is_saudi = normalized.endswith(".SR")
        return MarketSecurityResult(
            symbol=normalized[:-3] if is_saudi else normalized,
            market_symbol=normalized,
            name=str(metadata.get("longName") or metadata.get("shortName") or normalized),
            security_type="ETF" if str(metadata.get("instrumentType", "")).upper() == "ETF" else "STOCK",
            exchange="SAUDI_EXCHANGE" if is_saudi else _exchange_name(str(metadata.get("exchangeName") or metadata.get("fullExchangeName") or "GLOBAL")),
            currency_code="SAR" if is_saudi else str(metadata.get("currency") or "").upper(),
        )


class SahmkMarketSecuritySearch:
    """Complete Saudi symbol directory search (TASI and Nomu)."""

    BASE_URL = "https://api.sahmk.sa/api/v1"

    def __init__(self, api_key: str, timeout_seconds: float = 10.0):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _load(self, url: str) -> dict:
        request = Request(url, headers={"Accept": "application/json", "X-API-Key": self.api_key, "User-Agent": "WealthOS/0.1"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise MarketPriceProviderError("Could not search the complete Saudi securities directory.") from error

    def search(self, query: str, limit: int = 20) -> list[MarketSecurityResult]:
        normalized = query.strip()
        if len(normalized) < 2 or not self.api_key:
            return []
        payload = self._load(f"{self.BASE_URL}/companies/?{urlencode({'search': normalized, 'limit': limit, 'offset': 0})}")
        return [self._result(item) for item in payload.get("results", []) if item.get("symbol")]

    def resolve(self, symbol: str) -> MarketSecurityResult:
        code = symbol.upper().removesuffix(".SR")
        return self._result(self._load(f"{self.BASE_URL}/company/{code}/"))

    @staticmethod
    def _result(item: dict) -> MarketSecurityResult:
        symbol = str(item.get("symbol", "")).strip()
        raw_type = str(item.get("security_type") or item.get("type") or "STOCK").upper()
        security_type = "REIT" if "REIT" in raw_type else "ETF" if any(label in raw_type for label in ("ETF", "FUND", "CEF")) else "STOCK"
        return MarketSecurityResult(
            symbol=symbol,
            market_symbol=f"{symbol}.SR",
            name=str(item.get("name_en") or item.get("name") or symbol).strip(),
            security_type=security_type,
            exchange="SAUDI_EXCHANGE",
            currency_code="SAR",
        )


def _exchange_name(value: str) -> str:
    normalized = value.upper().strip()
    return {"NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ", "NYQ": "NYSE", "PCX": "NYSE_ARCA"}.get(normalized, normalized or "GLOBAL")
