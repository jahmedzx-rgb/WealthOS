from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class MarketPrice(Base):
    __tablename__ = "market_prices"
    __table_args__ = (
        Index(
            "ix_market_prices_security_price_date",
            "security_id",
            "price_date",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    security_id: Mapped[int] = mapped_column(
        ForeignKey("securities.id"),
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )

    price_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )
