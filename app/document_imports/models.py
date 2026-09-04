from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, default=1)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(30), default="PENDING_REVIEW", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    next_reminder_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC) + timedelta(days=3))
    operations = relationship("ImportedOperation", back_populates="batch", cascade="all, delete-orphan")
    user = relationship("User", back_populates="import_batches")


class ImportedOperation(Base):
    __tablename__ = "imported_operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id", ondelete="CASCADE"), index=True)
    operation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    transaction_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    card_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    matched_entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    matched_entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    posting_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    batch = relationship("ImportBatch", back_populates="operations")
