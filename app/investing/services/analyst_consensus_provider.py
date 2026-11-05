from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import json
from time import monotonic
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class AnalystConsensus:
    value: Decimal
    source: str
    median: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    recommendation: str | None = None
    analyst_count: int | None = None


class YahooAnalystConsensusProvider:
    BASE_URL = "https://query1.finance.yahoo.com/v10/finance/quoteSummary"

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds

    def get_mean_target(self, symbol: str) -> AnalystConsensus | None:
        request = Request(
            f"{self.BASE_URL}/{quote(symbol.strip().upper())}?modules=financialData",
            headers={"User-Agent": "Mozilla/5.0 WealthOS/1.0", "Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            financial = payload["quoteSummary"]["result"][0]["financialData"]
            raw = financial.get("targetMeanPrice")
            value = raw.get("raw") if isinstance(raw, dict) else raw
            consensus = Decimal(str(value))
            if consensus <= 0:
                return None
            return AnalystConsensus(consensus, "Yahoo Finance analyst consensus")
        except (OSError, ValueError, KeyError, IndexError, TypeError, InvalidOperation, json.JSONDecodeError):
            return None


class SahmkAnalystConsensusProvider:
    BASE_URL = "https://api.sahmk.sa/api/v1/company"

    def __init__(self, api_key: str, timeout_seconds: float = 10.0):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _decimal(value) -> Decimal | None:
        try:
            parsed = Decimal(str(value))
            return parsed if parsed > 0 else None
        except (InvalidOperation, TypeError, ValueError):
            return None

    def get_mean_target(self, symbol: str) -> AnalystConsensus | None:
        request = Request(
            f"{self.BASE_URL}/{quote(symbol.strip().upper())}/",
            headers={"X-API-Key": self.api_key, "Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            analysts = payload.get("analysts") or {}
            mean = self._decimal(analysts.get("target_mean"))
            if mean is None:
                return None
            count = analysts.get("num_analysts")
            return AnalystConsensus(
                value=mean,
                source="SAHMK analyst consensus",
                median=self._decimal(analysts.get("target_median")),
                high=self._decimal(analysts.get("target_high")),
                low=self._decimal(analysts.get("target_low")),
                recommendation=analysts.get("consensus"),
                analyst_count=int(count) if count is not None else None,
            )
        except (OSError, ValueError, KeyError, TypeError, InvalidOperation, json.JSONDecodeError):
            return None


class _SouqDataTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            value = data.strip()
            if value:
                self._cell.append(value)

    def handle_endtag(self, tag):
        if tag == "td" and self._cell is not None and self._row is not None:
            self._row.append(" ".join(self._cell))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


class SouqDataAnalystConsensusProvider:
    URL = "https://souqdata.com/insights/analyst-consensus"
    _cache: dict[str, AnalystConsensus] = {}
    _cache_time = 0.0
    CACHE_SECONDS = 6 * 60 * 60

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _price(value: str) -> Decimal | None:
        try:
            parsed = Decimal(value.replace("SAR", "").replace(",", "").strip())
            return parsed if parsed > 0 else None
        except (InvalidOperation, ValueError):
            return None

    def _load(self) -> dict[str, AnalystConsensus]:
        now = monotonic()
        if self.__class__._cache and now - self.__class__._cache_time < self.CACHE_SECONDS:
            return self.__class__._cache
        request = Request(self.URL, headers={"User-Agent": "Mozilla/5.0 WealthOS/1.0", "Accept": "text/html"})
        with urlopen(request, timeout=self.timeout_seconds) as response:
            parser = _SouqDataTableParser()
            parser.feed(response.read().decode("utf-8"))
        result: dict[str, AnalystConsensus] = {}
        for cells in parser.rows:
            if len(cells) < 9 or not cells[0].isdigit():
                continue
            low, mean, high = self._price(cells[6]), self._price(cells[7]), self._price(cells[8])
            if mean is None:
                continue
            try:
                count = int(cells[4])
            except ValueError:
                count = None
            result[cells[0]] = AnalystConsensus(mean, "SouqData broker consensus (daily)", None, high, low, cells[3], count)
        self.__class__._cache, self.__class__._cache_time = result, now
        return result

    def get_mean_target(self, symbol: str) -> AnalystConsensus | None:
        try:
            return self._load().get(symbol.strip().upper().removesuffix(".SR"))
        except (OSError, ValueError, UnicodeError):
            return None
