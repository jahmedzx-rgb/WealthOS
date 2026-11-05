from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class DistributionAnnouncement(Base):
    __tablename__ = "distribution_announcements"
    __table_args__ = (UniqueConstraint("user_id", "fingerprint", name="uq_distribution_announcement_fingerprint"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id", ondelete="CASCADE"), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(160), nullable=False)
    announcement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    eligibility_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_per_unit: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    eligible_quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    expected_gross_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    withholding_tax_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    expected_tax_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, default=0)
    expected_net_amount: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="IRREGULAR")
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ANNOUNCED")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
