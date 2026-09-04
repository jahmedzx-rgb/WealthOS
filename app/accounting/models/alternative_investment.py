from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AlternativeInvestment(Base):
    __tablename__ = "alternative_investments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_name: Mapped[str] = mapped_column(String(120), nullable=False)
    investment_name: Mapped[str] = mapped_column(String(160), nullable=False)
    investment_type: Mapped[str] = mapped_column(String(40), nullable=False)
    funding_bank_account_id: Mapped[int] = mapped_column(ForeignKey("bank_accounts.id"), nullable=False)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    current_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    expected_annual_return: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    amount_returned: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    investment_date: Mapped[date] = mapped_column(Date, nullable=False)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_distribution_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    distribution_frequency: Mapped[str | None] = mapped_column(String(24), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="SAR")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ACTIVE")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

