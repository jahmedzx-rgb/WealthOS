from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CreditCardAccount(Base):
    __tablename__ = "credit_card_accounts"
    __table_args__ = (UniqueConstraint("user_id", "last4", name="uq_user_credit_card_last4"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    issuer_bank: Mapped[str] = mapped_column(String(120), nullable=False)
    card_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last4: Mapped[str] = mapped_column(String(4), nullable=False)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    statement_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    minimum_monthly_payment: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    statement_cutoff_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_due_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_fee_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    annual_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    fee_renewal_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fee_renewal_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="SAR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
