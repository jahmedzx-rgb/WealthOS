import json
from pathlib import Path
import re

from app.investing.services.market_security_search import MarketSecurityResult


_PATH = Path(__file__).resolve().parents[1] / "data" / "us_securities.json"
_ALIASES = {"تسلا": "TSLA", "ابل": "AAPL", "أبل": "AAPL", "آبل": "AAPL"}


def _normalize(value: str) -> str:
    value = _ALIASES.get(value.strip(), value).lower().lstrip("$")
    return re.sub(r"[^a-z0-9]+", "", value)


_RECORDS = json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else []
_INDEX = [(item, _normalize(item["symbol"]), _normalize(item["name"])) for item in _RECORDS]


def search_us_catalog(query: str, limit: int = 10) -> list[MarketSecurityResult]:
    candidate = _normalize(query)
    if len(candidate) < 2 or not _PATH.exists():
        return []
    ranked = []
    for item, symbol, name in _INDEX:
        score = 0 if symbol == candidate else 1 if name == candidate else 2 if symbol.startswith(candidate) else 3 if name.startswith(candidate) else 4 if candidate in name else None
        if score is not None:
            ranked.append((score, len(item["name"]), item))
    return [MarketSecurityResult(symbol=item["symbol"], market_symbol=item["symbol"], name=item["name"], security_type=item["security_type"], exchange=item["exchange"], currency_code="USD") for _, _, item in sorted(ranked, key=lambda row:(row[0],row[1],row[2]["symbol"]))[:limit]]
