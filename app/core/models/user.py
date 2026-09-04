from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, JSON, UniqueConstraint, false
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username_normalized", name="uq_users_username_normalized"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    username_normalized: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    quick_action_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(80), nullable=True)
    country_of_residence: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tax_residence: Mapped[str | None] = mapped_column(String(80), nullable=True)
    investor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="INDIVIDUAL")
    default_dividend_withholding_tax_rate: Mapped[Decimal] = mapped_column(Numeric(8, 5), nullable=False, default=Decimal("0"))
    setup_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(2), default="en", server_default="en", nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="en", server_default="en", nullable=False)
    base_currency_code: Mapped[str] = mapped_column(String(3), default="SAR", server_default="SAR", nullable=False)
    enabled_currency_codes: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["SAR"], server_default='["SAR"]', nullable=False)
    local_data_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    setup_migration_choice: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recovery_code_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    security_state_version: Mapped[int] = mapped_column(default=1, server_default="1", nullable=False)
    failed_unlock_attempts: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    next_unlock_allowed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_recovery_attempts: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    next_recovery_allowed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lock_timeout_minutes: Mapped[int] = mapped_column(default=15, server_default="15", nullable=False)

    entities = relationship("Entity", back_populates="user")
    brokers = relationship("Broker", back_populates="user")
    journal_entries = relationship("JournalEntry", back_populates="user")
    loans = relationship("Loan", back_populates="user")
    import_batches = relationship("ImportBatch", back_populates="user")
