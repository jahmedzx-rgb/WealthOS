from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class DistributionEvent:
    distribution_date: date
    amount_per_unit: Decimal
    source: str
    eligibility_date: date | None = None
    date_kind: str = "payment"
    frequency: str = "IRREGULAR"


def infer_distribution_frequency(event_dates: list[date]) -> str:
    """Infer a conservative recurrence from actual distribution history."""
    ordered = sorted(set(event_dates))
    if len(ordered) < 2:
        return "IRREGULAR"
    intervals = sorted((right - left).days for left, right in zip(ordered, ordered[1:]) if right > left)
    if not intervals:
        return "IRREGULAR"
    typical = intervals[len(intervals) // 2]
    if 5 <= typical <= 10:
        return "WEEKLY"
    if 20 <= typical <= 40:
        return "MONTHLY"
    if 70 <= typical <= 110:
        return "QUARTERLY"
    if 150 <= typical <= 220:
        return "SEMI_ANNUAL"
    if 300 <= typical <= 430:
        return "ANNUAL"
    return "IRREGULAR"


class DistributionProviderError(RuntimeError):
    pass


class SahmkDistributionProvider:
    BASE_URL = "https://app.sahmk.sa/api/v1/dividends"

    def __init__(self, api_key: str, timeout_seconds: float = 10.0):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def get_upcoming(self, symbol: str) -> DistributionEvent | None:
        if not self.api_key:
            return None
        code = symbol.split(".", 1)[0].strip()
        payload = _load_json(
            f"{self.BASE_URL}/{code}/?{urlencode({'limit': 10})}",
            self.timeout_seconds,
            {"Authorization": f"Bearer {self.api_key}"},
        )
        history_dates: list[date] = []
        for item in [*payload.get("history", []), *payload.get("upcoming", [])]:
            raw_date = item.get("distribution_date")
            if raw_date:
                try:
                    history_dates.append(date.fromisoformat(raw_date))
                except ValueError:
                    pass
        frequency = infer_distribution_frequency(history_dates)
        candidates: list[DistributionEvent] = []
        for item in payload.get("upcoming", []):
            try:
                payment_date = date.fromisoformat(item["distribution_date"])
                amount = Decimal(str(item["value"]))
                eligibility = date.fromisoformat(item["eligibility_date"]) if item.get("eligibility_date") else None
            except (KeyError, TypeError, ValueError, InvalidOperation):
                continue
            if payment_date >= date.today() and amount > 0:
                candidates.append(DistributionEvent(payment_date, amount, "Saudi Exchange via SAHMK", eligibility, frequency=frequency))
        return min(candidates, key=lambda event: event.distribution_date) if candidates else None


class VerifiedSaudiExchangeDistributionProvider:
    """Short-lived fallback for distributions verified against official announcements."""

    EVENTS = {
        "4348": DistributionEvent(
            distribution_date=date(2026, 10, 21),
            amount_per_unit=Decimal("0.105"),
            source="Saudi Exchange official announcement",
            eligibility_date=date(2026, 8, 11),
            frequency="QUARTERLY",
        ),
    }

    def get_upcoming(self, symbol: str) -> DistributionEvent | None:
        code = symbol.split(".", 1)[0].strip()
        event = self.EVENTS.get(code)
        return event if event and event.distribution_date >= date.today() else None


class YahooDistributionProvider:
    """Fallback for declared dividend events. Yahoo dates are ex-dividend dates."""

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds

    def get_upcoming(self, symbol: str) -> DistributionEvent | None:
        query = urlencode({"range": "2y", "interval": "1d", "events": "div"})
        payload = _load_json(f"{self.BASE_URL}/{symbol}?{query}", self.timeout_seconds)
        try:
            events = payload["chart"]["result"][0].get("events", {}).get("dividends", {}).values()
        except (KeyError, IndexError, TypeError):
            return None
        parsed_events: list[tuple[date, Decimal]] = []
        for item in events:
            try:
                event_date = datetime.fromtimestamp(int(item["date"]), tz=timezone.utc).date()
                amount = Decimal(str(item["amount"]))
            except (KeyError, TypeError, ValueError, InvalidOperation):
                continue
            if amount > 0:
                parsed_events.append((event_date, amount))
        frequency = infer_distribution_frequency([item[0] for item in parsed_events])
        candidates = [DistributionEvent(event_date, amount, "Yahoo Finance", event_date, "eligibility", frequency)
                      for event_date, amount in parsed_events if event_date >= date.today()]
        return min(candidates, key=lambda event: event.distribution_date) if candidates else None


class MultiSourceDistributionProvider:
    def __init__(self, providers):
        self.providers = providers

    def get_upcoming(self, symbol: str) -> tuple[DistributionEvent | None, list[str]]:
        checked: list[str] = []
        for provider in self.providers:
            checked.append(type(provider).__name__.replace("DistributionProvider", ""))
            try:
                event = provider.get_upcoming(symbol)
            except DistributionProviderError:
                continue
            if event is not None:
                return event, checked
        return None, checked


def _load_json(url: str, timeout_seconds: float, headers: dict[str, str] | None = None) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "WealthOS/0.1", **(headers or {})})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise DistributionProviderError("Could not load distribution data.") from error
    if not isinstance(payload, dict):
        raise DistributionProviderError("Distribution provider returned invalid data.")
    return payload
