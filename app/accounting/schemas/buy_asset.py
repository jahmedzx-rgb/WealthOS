from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class BuyAssetRequest(BaseModel):
    asset_account_code: int = Field(..., gt=0)
    payment_source: str = Field(pattern="^(BANK_ACCOUNT|CASH_ON_HAND)$")
    bank_account_id: int | None = Field(default=None, gt=0)
    amount: Decimal = Field(..., gt=0)
    transaction_date: datetime
    description: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_payment_source(self):
        if self.payment_source == "BANK_ACCOUNT" and self.bank_account_id is None:
            raise ValueError("Select the bank account used for this purchase.")
        return self
