from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
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
            {"X-API-Key": self.api_key},
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
        "4336": DistributionEvent(
            # The issuer states payment will be made within 35 business days;
            # use the end of that window as the expected payment date.
            distribution_date=date(2026, 12, 17),
            amount_per_unit=Decimal("0.08"),
            source="Mulkia official announcement — payable within 35 business days",
            eligibility_date=date(2026, 11, 2),
            frequency="QUARTERLY",
        ),
        "7010": DistributionEvent(
            distribution_date=date(2026, 11, 19),
            amount_per_unit=Decimal("0.55"),
            source="Saudi Exchange official announcement",
            eligibility_date=date(2026, 11, 2),
            frequency="QUARTERLY",
        ),
    }

    def get_upcoming(self, symbol: str) -> DistributionEvent | None:
        code = symbol.split(".", 1)[0].strip()
        event = self.EVENTS.get(code)
        return event if event and event.distribution_date >= date.today() else None


class VerifiedFundDistributionProvider:
    """Time-bounded official fund announcements used before market feeds normalize the event."""

    EVENTS = {
        "GPTY": (
            DistributionEvent(date(2026, 10, 29), Decimal("0.2620"), "YieldMax official distribution schedule", date(2026, 10, 28), frequency="WEEKLY"),
            DistributionEvent(date(2026, 11, 5), Decimal("0.2433"), "YieldMax official distribution schedule", date(2026, 11, 5), frequency="WEEKLY"),
            DistributionEvent(date(2026, 11, 13), Decimal("0.2407"), "YieldMax official distribution schedule", date(2026, 11, 12), frequency="WEEKLY"),
        ),
        "FEPI": (
            DistributionEvent(date(2026, 10, 29), Decimal("0.1964"), "REX Shares official distribution schedule", date(2026, 10, 28), frequency="WEEKLY"),
            DistributionEvent(date(2026, 11, 5), Decimal("0.1833"), "REX Shares official distribution schedule", date(2026, 11, 4), frequency="WEEKLY"),
            DistributionEvent(date(2026, 11, 13), Decimal("0.1798"), "REX Shares official distribution schedule", date(2026, 11, 12), frequency="WEEKLY"),
        ),
        "QUSA": (
            DistributionEvent(date(2026, 10, 27), Decimal("0.20825"), "VistaShares official distribution schedule", date(2026, 10, 26), frequency="MONTHLY"),
        ),
        "IYRI": (
            DistributionEvent(date(2026, 10, 23), Decimal("0.4113"), "NEOS official distribution schedule", date(2026, 10, 21), frequency="MONTHLY"),
        ),
    }

    def get_recent(self, symbol: str, since: date | None = None) -> list[DistributionEvent]:
        code = symbol.split(".", 1)[0].strip().upper()
        cutoff = since or date.today() - timedelta(days=365)
        return [event for event in self.EVENTS.get(code, ()) if event.distribution_date >= cutoff]

    def get_upcoming(self, symbol: str) -> DistributionEvent | None:
        events = self.get_recent(symbol)
        return max(events, key=lambda event: event.distribution_date) if events else None


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

    def get_trailing_year_summary(self, symbol: str) -> tuple[Decimal | None, str | None]:
        query = urlencode({"range": "1y", "interval": "1d", "events": "div"})
        payload = _load_json(f"{self.BASE_URL}/{symbol}?{query}", self.timeout_seconds)
        try:
            events = payload["chart"]["result"][0].get("events", {}).get("dividends", {}).values()
        except (KeyError, IndexError, TypeError):
            return None, None
        cutoff = date.today() - timedelta(days=365)
        total = Decimal("0")
        distribution_dates: list[date] = []
        for item in events:
            try:
                event_date = datetime.fromtimestamp(int(item["date"]), tz=timezone.utc).date()
                amount = Decimal(str(item["amount"]))
            except (KeyError, TypeError, ValueError, InvalidOperation):
                continue
            if cutoff <= event_date <= date.today() and amount > 0:
                total += amount
                distribution_dates.append(event_date)
        return (total if total > 0 else None,
                infer_distribution_frequency(distribution_dates) if distribution_dates else None)

    def get_trailing_year_total(self, symbol: str) -> Decimal | None:
        total, _ = self.get_trailing_year_summary(symbol)
        return total


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

    def get_events(self, symbol: str) -> tuple[list[DistributionEvent], list[str]]:
        checked: list[str] = []
        for provider in self.providers:
            checked.append(type(provider).__name__.replace("DistributionProvider", ""))
            try:
                events = provider.get_recent(symbol) if hasattr(provider, "get_recent") else []
                if not events:
                    event = provider.get_upcoming(symbol)
                    events = [event] if event is not None else []
            except DistributionProviderError:
                continue
            if events:
                return events, checked
        return [], checked


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
