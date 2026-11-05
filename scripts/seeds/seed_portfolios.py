from app.investing.models.portfolio import Portfolio


def seed_portfolios(db):
    portfolios = [
        Portfolio(
            code="RETIREMENT",
            name="Retirement Portfolio",
            entity_id=1,
            strategy_id=1,
            objective_id=1,
            base_currency_id=1,
            description="Long-term retirement portfolio.",
        ),
        Portfolio(
            code="DIVIDEND",
            name="Dividend Portfolio",
            entity_id=1,
            strategy_id=2,
            objective_id=2,
            base_currency_id=1,
            description="Dividend income portfolio.",
        ),
        Portfolio(
            code="TRADING",
            name="Trading Portfolio",
            entity_id=1,
            strategy_id=5,
            objective_id=5,
            base_currency_id=1,
            description="Active trading portfolio.",
        ),
    ]

    db.add_all(portfolios)
from app.database.engine import SessionLocal

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_portfolios(db)
        db.commit()
        print("Portfolios seeded successfully.")
    finally:
        db.close()
