from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class WealthAnalyticsSnapshot(Base):
    __tablename__ = "wealth_analytics_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "snapshot_date", name="uq_wealth_analytics_snapshot_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_assets: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    total_liabilities: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    net_worth: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    available_cash: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
