from sqlalchemy.orm import Session

from app.investing.application.portfolio_engine import (
    PortfolioEngine,
)


class WealthSummaryEngine:
    def __init__(self, db: Session):
        self.db = db
        self.portfolio_engine = (
            PortfolioEngine(db)
        )

    def get_summary(
        self,
        portfolio_id: int,
    ):
        portfolio = (
            self.portfolio_engine.get_summary(
                portfolio_id
            )
        )

        return {
            "portfolio": portfolio,
        }
