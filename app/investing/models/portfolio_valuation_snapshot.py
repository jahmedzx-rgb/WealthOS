from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PortfolioValuationSnapshot(Base):
    __tablename__ = "portfolio_valuation_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "portfolio_id", "valuation_date", name="uq_portfolio_snapshot_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # A null portfolio identifies the user's consolidated investment snapshot.
    portfolio_id: Mapped[int | None] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True, index=True)
    valuation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    market_value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    total_return: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    positions_snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True)
    historical_portfolio_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    positions_as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    positions_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_month_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
