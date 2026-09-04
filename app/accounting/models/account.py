from sqlalchemy import (
    String,
    Integer,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    account_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # DEBIT or CREDIT
    normal_balance: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=True,
    )

    level: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    is_header: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    allow_posting: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    parent = relationship(
        "Account",
        remote_side=[id],
        backref="children",
    )