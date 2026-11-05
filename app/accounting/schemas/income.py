from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class IncomeRequest(BaseModel):
    income_source: str = Field(..., min_length=1, max_length=120)

    accounting_category: str | None = Field(
        default=None,
        max_length=40,
    )

    destination_account_code: int = Field(
        ...,
        gt=0,
    )
    destination_bank_account_id: int | None = Field(default=None, gt=0)
    destination_credit_card_id: int | None = Field(default=None, gt=0)

    amount: Decimal = Field(
        ...,
        gt=0,
    )

    transaction_date: datetime

    description: str = Field(
        default="Income",
        max_length=255,
    )

    linked_source: str | None = Field(
        default=None,
        max_length=200,
    )

    rent_frequency: str | None = Field(default=None, pattern="^(MONTHLY|QUARTERLY|SEMI_ANNUAL|ANNUAL)$")
    next_rent_due_date: date | None = None
    rent_property_name: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def validate_destination(self):
        destinations = sum(value is not None for value in (
            self.destination_bank_account_id,
            self.destination_credit_card_id,
        ))
        if destinations > 1:
            raise ValueError("Select only one income destination.")
        return self
