from app.investing.models.portfolio_strategy import PortfolioStrategy


def seed_portfolio_strategies(db):
    strategies = [
        PortfolioStrategy(
            code="LONG_TERM",
            name="Long-Term Investing",
            description="Long-term buy and hold strategy.",
        ),
        PortfolioStrategy(
            code="DIVIDEND",
            name="Dividend Investing",
            description="Income-focused dividend strategy.",
        ),
        PortfolioStrategy(
            code="GROWTH",
            name="Growth Investing",
            description="Growth stock strategy.",
        ),
        PortfolioStrategy(
            code="VALUE",
            name="Value Investing",
            description="Value investing strategy.",
        ),
        PortfolioStrategy(
            code="TRADING",
            name="Active Trading",
            description="Short-term trading strategy.",
        ),
    ]

    db.add_all(strategies)

from app.database.engine import SessionLocal

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_portfolio_strategies(db)
        db.commit()
        print("Portfolio strategies seeded successfully.")
    finally:
        db.close()
