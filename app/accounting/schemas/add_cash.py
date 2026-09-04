from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AddCashRequest(BaseModel):
    portfolio_id: int = Field(..., gt=0)
    source_bank_account_id: int = Field(..., gt=0)

    amount: Decimal = Field(..., gt=0)

    transaction_date: datetime

    description: str = Field(
        default="Cash Deposit",
        max_length=255,
    )
