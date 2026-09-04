from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.investing.models.portfolio_valuation_snapshot import PortfolioValuationSnapshot


class PortfolioHistoryService:
    PERIOD_DAYS = {"1W": 7, "1M": 30, "1Y": 365}

    def __init__(self, db: Session):
        self.db = db

    def record(self, user_id: int, portfolio_id: int | None, summary: dict) -> PortfolioValuationSnapshot:
        today = datetime.now(UTC).date()
        snapshot = self.db.query(PortfolioValuationSnapshot).filter(
            PortfolioValuationSnapshot.user_id == user_id,
            PortfolioValuationSnapshot.portfolio_id == portfolio_id,
            PortfolioValuationSnapshot.valuation_date == today,
        ).first()
        if snapshot is None:
            snapshot = PortfolioValuationSnapshot(user_id=user_id, portfolio_id=portfolio_id, valuation_date=today)
            self.db.add(snapshot)
        snapshot.market_value = Decimal(str(summary["market_value"]))
        snapshot.total_cost = Decimal(str(summary["total_cost"]))
        snapshot.total_return = Decimal(str(summary["total_return"]))
        snapshot.recorded_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def get(self, user_id: int, portfolio_id: int | None, period: str) -> dict:
        today = datetime.now(UTC).date()
        if period == "YTD":
            start = date(today.year, 1, 1)
        else:
            start = today - timedelta(days=self.PERIOD_DAYS.get(period, 36500))
        snapshots = self.db.query(PortfolioValuationSnapshot).filter(
            PortfolioValuationSnapshot.user_id == user_id,
            PortfolioValuationSnapshot.portfolio_id == portfolio_id,
            PortfolioValuationSnapshot.valuation_date >= start,
        ).order_by(PortfolioValuationSnapshot.valuation_date).all()
        points = [{"date": item.valuation_date, "market_value": item.market_value, "total_cost": item.total_cost, "total_return": item.total_return} for item in snapshots]
        sufficient = len(points) >= 2
        change = Decimal("0")
        percentage = Decimal("0")
        if sufficient:
            first = Decimal(str(points[0]["market_value"]))
            last = Decimal(str(points[-1]["market_value"]))
            change = last - first
            percentage = Decimal("0") if first == 0 else (change / first) * Decimal("100")
        return {"period": period, "has_sufficient_history": sufficient, "change": change, "percentage": percentage, "points": points}
