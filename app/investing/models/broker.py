from decimal import Decimal
from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Broker(Base):
    __tablename__ = "brokers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, default=1)

    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    country: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    institution_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    execution_partner: Mapped[str | None] = mapped_column(String(100), nullable=True)

    commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
    commission_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    commission_tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
    commission_tax_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    dividend_withholding_tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
    dividend_withholding_tax_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    user = relationship("User", back_populates="brokers")
