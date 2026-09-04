from datetime import datetime

from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id"),
        nullable=False,
    )

    account_identifier: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    portfolio_number: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    broker_id: Mapped[int | None] = mapped_column(
        ForeignKey("brokers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("portfolio_strategies.id"),
        nullable=False,
    )

    objective_id: Mapped[int] = mapped_column(
        ForeignKey("portfolio_objectives.id"),
        nullable=False,
    )

    base_currency_id: Mapped[int] = mapped_column(
        ForeignKey("currencies.id"),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
    )

    entity = relationship("Entity")
    broker = relationship("Broker")
    strategy = relationship("PortfolioStrategy")
    objective = relationship("PortfolioObjective")
    base_currency = relationship("Currency")
