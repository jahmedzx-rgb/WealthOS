from datetime import UTC, date, datetime

from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PropertyAsset(Base):
    __tablename__ = "property_assets"
    __table_args__ = (UniqueConstraint("acquisition_journal_entry_id"), UniqueConstraint("user_id", "external_reference", name="uq_property_user_external_reference"))

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    acquisition_journal_entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    usage: Mapped[str] = mapped_column(String(30), nullable=False, default="UNSPECIFIED")
    income_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    current_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    acquisition_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    improvement_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    purchase_price_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    improvement_cost_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    opening_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    opening_market_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    market_value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    market_value_source: Mapped[str | None] = mapped_column(String(160), nullable=True)
    market_value_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    valuation_journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class PropertyOpeningAudit(Base):
    __tablename__ = "property_opening_audits"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_property_opening_user_idempotency"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("property_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    similarity_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
