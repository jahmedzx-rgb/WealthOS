from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CardPaymentRequest(BaseModel):
    credit_card_id: int = Field(..., gt=0)
    bank_account_id: int = Field(..., gt=0)

    credit_card_account_code: int = Field(
        ...,
        gt=0,
    )

    payment_account_code: int = Field(
        ...,
        gt=0,
    )

    amount: Decimal = Field(
        ...,
        gt=0,
    )

    transaction_date: datetime

    description: str = Field(
        default="Credit Card Payment",
        max_length=255,
    )
