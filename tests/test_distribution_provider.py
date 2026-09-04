from datetime import date, timedelta
from decimal import Decimal

from app.investing.services.distribution_provider import (
    DistributionEvent,
    MultiSourceDistributionProvider,
    VerifiedSaudiExchangeDistributionProvider,
    infer_distribution_frequency,
)


class EmptyProvider:
    def get_upcoming(self, symbol):
        return None


class ConfirmedProvider:
    def get_upcoming(self, symbol):
        return DistributionEvent(date.today() + timedelta(days=2), Decimal("0.55"), "Saudi Exchange via Test")


def test_multi_source_distribution_provider_falls_back_in_order():
    event, checked = MultiSourceDistributionProvider([EmptyProvider(), ConfirmedProvider()]).get_upcoming("7010.SR")
    assert event is not None
    assert event.amount_per_unit == Decimal("0.55")
    assert event.date_kind == "payment"
    assert checked == ["EmptyProvider", "ConfirmedProvider"]


def test_multi_source_distribution_provider_reports_all_checked_sources():
    event, checked = MultiSourceDistributionProvider([EmptyProvider(), EmptyProvider()]).get_upcoming("AAPL")
    assert event is None
    assert checked == ["EmptyProvider", "EmptyProvider"]


def test_verified_alkhabeer_distribution_matches_official_announcement():
    event = VerifiedSaudiExchangeDistributionProvider().get_upcoming("4348.SR")
    assert event is not None
    assert event.distribution_date == date(2026, 10, 21)
    assert event.eligibility_date == date(2026, 8, 11)
    assert event.amount_per_unit == Decimal("0.105")
    assert event.source == "Saudi Exchange official announcement"
    assert event.frequency == "QUARTERLY"


def test_distribution_frequency_is_inferred_from_actual_intervals():
    assert infer_distribution_frequency([date(2026, 1, 1), date(2026, 4, 2), date(2026, 7, 2)]) == "QUARTERLY"
    assert infer_distribution_frequency([date(2026, 1, 1), date(2026, 2, 1)]) == "MONTHLY"
    assert infer_distribution_frequency([date(2026, 1, 1)]) == "IRREGULAR"
