from app.investing.models.portfolio_objective import PortfolioObjective


def seed_portfolio_objectives(db):
    objectives = [
        PortfolioObjective(
            code="RETIREMENT",
            name="Retirement",
            description="Build long-term retirement wealth.",
        ),
        PortfolioObjective(
            code="PASSIVE_INCOME",
            name="Passive Income",
            description="Generate recurring income.",
        ),
        PortfolioObjective(
            code="WEALTH_GROWTH",
            name="Wealth Growth",
            description="Maximize long-term capital appreciation.",
        ),
        PortfolioObjective(
            code="CAPITAL_PRESERVATION",
            name="Capital Preservation",
            description="Protect capital with low risk.",
        ),
        PortfolioObjective(
            code="SPECULATION",
            name="Speculation",
            description="High-risk, high-return investing.",
        ),
    ]

    db.add_all(objectives)

from app.database.engine import SessionLocal

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_portfolio_objectives(db)
        db.commit()
        print("Portfolio objectives seeded successfully.")
    finally:
        db.close()
