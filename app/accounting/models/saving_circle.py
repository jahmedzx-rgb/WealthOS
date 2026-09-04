from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SavingCircle(Base):
    __tablename__ = "saving_circles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_name: Mapped[str] = mapped_column(String(120), nullable=False)
    circle_name: Mapped[str] = mapped_column(String(140), nullable=False)
    installment_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    total_installments: Mapped[int] = mapped_column(nullable=False)
    payout_installment: Mapped[int] = mapped_column(nullable=False)
    installments_paid: Mapped[int] = mapped_column(nullable=False, default=0)
    amount_received: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payout_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    funding_bank_account_id: Mapped[int] = mapped_column(ForeignKey("bank_accounts.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


