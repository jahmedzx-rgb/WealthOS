from app.investing.models.security import Security


def seed_securities(db):
    securities = [
        Security(
            symbol="AAPL",
            name="Apple Inc.",
            security_type="STOCK",
            exchange="NASDAQ",
            currency_code="USD",
        ),
        Security(
            symbol="MSFT",
            name="Microsoft Corporation",
            security_type="STOCK",
            exchange="NASDAQ",
            currency_code="USD",
        ),
        Security(
            symbol="NVDA",
            name="NVIDIA Corporation",
            security_type="STOCK",
            exchange="NASDAQ",
            currency_code="USD",
        ),
        Security(
            symbol="SPY",
            name="SPDR S&P 500 ETF",
            security_type="ETF",
            exchange="NYSE",
            currency_code="USD",
        ),
        Security(
            symbol="QQQ",
            name="Invesco QQQ Trust",
            security_type="ETF",
            exchange="NASDAQ",
            currency_code="USD",
        ),
        Security(symbol="1120", market_symbol="1120.SR", name="Al Rajhi Bank", security_type="STOCK", exchange="SAUDI_EXCHANGE", currency_code="SAR"),
        Security(symbol="1180", market_symbol="1180.SR", name="Saudi National Bank", security_type="STOCK", exchange="SAUDI_EXCHANGE", currency_code="SAR"),
        Security(symbol="2010", market_symbol="2010.SR", name="SABIC", security_type="STOCK", exchange="SAUDI_EXCHANGE", currency_code="SAR"),
        Security(symbol="2222", market_symbol="2222.SR", name="Saudi Aramco", security_type="STOCK", exchange="SAUDI_EXCHANGE", currency_code="SAR"),
        Security(symbol="7010", market_symbol="7010.SR", name="stc", security_type="STOCK", exchange="SAUDI_EXCHANGE", currency_code="SAR"),
    ]

    db.add_all(securities)
from app.database.engine import SessionLocal

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_securities(db)
        db.commit()
        print("Securities seeded successfully.")
    finally:
        db.close()
