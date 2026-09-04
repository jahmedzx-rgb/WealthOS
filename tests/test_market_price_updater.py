from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.investing.services.market_price_provider import MarketQuote
from app.investing.services.market_price_updater import (
    MarketPriceUpdater,
)


def make_security(
    security_id: int = 1,
    symbol: str = "AAPL",
    is_active: bool = True,
):
    return SimpleNamespace(
        id=security_id,
        symbol=symbol,
        is_active=is_active,
    )


def make_updater():
    db = Mock()
    provider = Mock()
    updater = MarketPriceUpdater(db, provider)
    updater.security_repository = Mock()
    updater.market_price_service = Mock()
    return updater, db, provider


def test_update_security_records_provider_quote_and_commits():
    updater, db, provider = make_updater()
    security = make_security()
    quote = MarketQuote(
        price=Decimal("231.45"),
        price_date=datetime(2026, 8, 5),
    )
    market_price = Mock()
    updater.security_repository.get.return_value = security
    provider.get_latest.return_value = quote
    updater.market_price_service.record.return_value = market_price

    result = updater.update_security(security.id)

    provider.get_latest.assert_called_once_with("AAPL")
    updater.market_price_service.record.assert_called_once_with(
        security_id=1,
        price=Decimal("231.45"),
        price_date=datetime(2026, 8, 5),
    )
    db.commit.assert_called_once_with()
    db.refresh.assert_called_once_with(market_price)
    assert result is market_price


def test_update_security_uses_provider_symbol_for_saudi_exchange():
    updater, db, provider = make_updater()
    security = make_security(symbol="1120")
    security.market_symbol = "1120.SR"
    updater.security_repository.get.return_value = security
    provider.get_latest.return_value = MarketQuote(price=Decimal("92.50"), price_date=datetime(2026, 8, 7))
    updater.market_price_service.record.return_value = Mock()

    updater.update_security(security.id)

    provider.get_latest.assert_called_once_with("1120.SR")


def test_update_security_rolls_back_when_provider_fails():
    updater, db, provider = make_updater()
    updater.security_repository.get.return_value = make_security()
    provider.get_latest.side_effect = RuntimeError("provider failed")

    with pytest.raises(RuntimeError, match="provider failed"):
        updater.update_security(1)

    db.rollback.assert_called_once_with()
    db.commit.assert_not_called()


def test_update_all_only_updates_active_securities():
    updater, db, provider = make_updater()
    active = make_security(1, "AAPL", True)
    inactive = make_security(2, "OLD", False)
    quote = MarketQuote(
        price=Decimal("231.45"),
        price_date=datetime(2026, 8, 5),
    )
    market_price = Mock()
    updater.security_repository.list.return_value = [
        active,
        inactive,
    ]
    provider.get_latest.return_value = quote
    updater.market_price_service.record.return_value = market_price

    result = updater.update_all()

    provider.get_latest.assert_called_once_with("AAPL")
    db.commit.assert_called_once_with()
    assert result == [market_price]
