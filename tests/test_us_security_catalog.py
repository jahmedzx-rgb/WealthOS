import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.investing import register_market_security
from app.database.base import Base
from app.investing.models.security import Security
from app.investing.schemas.security import MarketSecurityRequest
from app.investing.services.us_security_catalog import search_us_catalog


@pytest.mark.parametrize("query", ["TSLA", "$TSLA", "tesla", "Tesla", "تسلا"])
def test_tesla_can_be_found_by_symbol_english_and_arabic(query):
    results = search_us_catalog(query)
    assert results
    assert results[0].symbol == "TSLA"


@pytest.mark.parametrize("query", ["AAPL", "$AAPL", "apple", "Apple", "أبل", "ابل", "آبل"])
def test_apple_can_be_found_by_symbol_english_and_arabic(query):
    results = search_us_catalog(query)
    assert results
    assert results[0].symbol == "AAPL"


def test_us_etfs_and_reits_are_searchable_and_classified():
    assert search_us_catalog("SPY")[0].security_type == "ETF"
    assert search_us_catalog("APLE")[0].security_type == "REIT"


@pytest.mark.parametrize(
    ("symbol", "security_type", "exchange"),
    [
        ("TSLA", "STOCK", "NASDAQ"),
        ("AAPL", "STOCK", "NASDAQ"),
        ("MSFT", "STOCK", "NASDAQ"),
        ("NVDA", "STOCK", "NASDAQ"),
        ("AMZN", "STOCK", "NASDAQ"),
        ("SPY", "ETF", "NYSE_ARCA"),
        ("QQQ", "ETF", "NASDAQ"),
        ("APLE", "REIT", "NYSE"),
    ],
)
def test_us_security_registration_uses_local_catalog_without_yahoo(
    monkeypatch,
    symbol,
    security_type,
    exchange,
):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Security.__table__])
    db = sessionmaker(bind=engine)()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Yahoo must not be called for a security in the local catalog")

    monkeypatch.setattr(
        "app.api.v1.investing.YahooMarketSecuritySearch.resolve",
        fail_if_called,
    )

    result = register_market_security(
        MarketSecurityRequest(
            symbol=symbol,
            market_symbol=symbol,
            name=f"{symbol} security",
            security_type=security_type,
            exchange="NASDAQ",
            currency_code="USD",
        ),
        db,
    )

    assert result["symbol"] == symbol
    assert result["security_type"] == security_type
    assert result["currency_code"] == "USD"
    assert result["exchange"] == exchange
