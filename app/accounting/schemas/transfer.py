from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TransferRequest(BaseModel):
    from_account_code: int = Field(..., gt=0)

    to_account_code: int = Field(..., gt=0)

    from_bank_account_id: int | None = Field(default=None, gt=0)

    to_bank_account_id: int | None = Field(default=None, gt=0)

    amount: Decimal = Field(..., gt=0)

    transaction_date: datetime

    description: str = Field(
        default="Transfer Funds",
        max_length=255,
    )
