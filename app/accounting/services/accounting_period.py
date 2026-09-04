from datetime import UTC, date, datetime, time, timedelta, timezone


# Saudi Arabia has used UTC+03:00 without daylight-saving transitions since 1947.
# A fixed offset keeps the packaged Windows beta independent of an external tzdata bundle.
ACCOUNTING_TIMEZONE = timezone(timedelta(hours=3), "Asia/Riyadh")


def riyadh_today() -> date:
    return datetime.now(ACCOUNTING_TIMEZONE).date()


def normalize_accounting_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ACCOUNTING_TIMEZONE)
    return value.astimezone(UTC)


def period_utc_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """Return an inclusive Riyadh date range as [UTC start, UTC end)."""
    local_start = datetime.combine(start_date, time.min, tzinfo=ACCOUNTING_TIMEZONE)
    local_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=ACCOUNTING_TIMEZONE)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)
