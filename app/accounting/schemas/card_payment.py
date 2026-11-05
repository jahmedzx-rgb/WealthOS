from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class CardPaymentRequest(BaseModel):
    credit_card_id: int = Field(..., gt=0)
    bank_account_id: int | None = Field(default=None, gt=0)
    payment_credit_card_id: int | None = Field(default=None, gt=0)

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

    @model_validator(mode="after")
    def validate_payment_source(self):
        if (self.bank_account_id is None) == (self.payment_credit_card_id is None):
            raise ValueError("Select exactly one payment source.")
        if self.payment_credit_card_id == self.credit_card_id:
            raise ValueError("A credit card cannot pay itself.")
        return self
