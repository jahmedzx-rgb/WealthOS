from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)

    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id"),
        nullable=False,
    )

    security_id: Mapped[int] = mapped_column(
        ForeignKey("securities.id"),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        default=0,
        nullable=False,
    )

    average_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        default=0,
        nullable=False,
    )

    next_distribution_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_distribution_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    distribution_frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fair_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )
