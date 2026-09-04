from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.investing.enums.trade_type import TradeType


class BuyStockRequest(BaseModel):
    portfolio_id: int = Field(..., gt=0)
    broker_id: int = Field(..., gt=0)
    security_id: int = Field(..., gt=0)

    side: TradeType

    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    commission: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
    )

    trade_date: datetime
    next_distribution_date: date | None = None
    expected_distribution_amount: Decimal | None = Field(default=None, ge=0)
    distribution_frequency: str | None = Field(default=None, pattern="^(WEEKLY|MONTHLY|QUARTERLY|SEMI_ANNUAL|ANNUAL|IRREGULAR)$")
    fair_value: Decimal | None = Field(default=None, gt=0)
