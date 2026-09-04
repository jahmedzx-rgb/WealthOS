from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OpeningCashRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    transaction_date: datetime
    description: str = Field(default="Opening Cash On Hand", min_length=1, max_length=255)


class OpeningCashAdjustmentRequest(BaseModel):
    corrected_balance: Decimal = Field(ge=0)
    transaction_date: datetime
    reason: str = Field(min_length=3, max_length=255)
