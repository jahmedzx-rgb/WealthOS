from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class BuyPropertyRequest(BaseModel):
    property_account_code: int = Field(
        ...,
        gt=0,
    )

    payment_source: str = Field(pattern="^(BANK_ACCOUNT|CASH_ON_HAND)$")

    bank_account_id: int | None = Field(default=None, gt=0)

    amount: Decimal = Field(
        ...,
        gt=0,
    )

    transfer_tax: Decimal = Field(default=0, ge=0)

    property_name: str | None = Field(default=None, min_length=1, max_length=160)

    property_usage: str = Field(default="UNSPECIFIED", pattern="^(PRIMARY_RESIDENCE|INVESTMENT_PROPERTY|VACATION_HOME|OTHER|UNSPECIFIED)$")

    property_income_type: str | None = Field(default=None, pattern="^(RESIDENTIAL_RENT|COMMERCIAL_RENT|SHORT_TERM_RENT)$")

    transaction_date: datetime

    description: str = Field(
        default="Buy Property",
        max_length=255,
    )

    @model_validator(mode="after")
    def validate_payment_source(self):
        if self.payment_source == "BANK_ACCOUNT" and self.bank_account_id is None:
            raise ValueError("Select the bank account used for this purchase.")
        if self.property_usage == "INVESTMENT_PROPERTY" and self.property_income_type is None:
            raise ValueError("Select the real estate income type for this investment property.")
        if self.property_usage != "INVESTMENT_PROPERTY":
            self.property_income_type = None
        return self
