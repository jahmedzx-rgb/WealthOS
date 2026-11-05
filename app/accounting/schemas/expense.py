from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class ExpenseRequest(BaseModel):
    expense_account_code: int = Field(..., gt=0)
    payment_bank_account_id: int | None = Field(default=None, gt=0)
    payment_credit_card_id: int | None = Field(default=None, gt=0)
    property_id: int | None = Field(default=None, gt=0)
    amount: Decimal = Field(..., gt=0)
    transaction_date: datetime
    description: str = Field(..., min_length=1, max_length=255)

    @model_validator(mode='after')
    def one_payment_source(self):
        if (self.payment_bank_account_id is None) == (self.payment_credit_card_id is None):
            raise ValueError('Select exactly one bank account or credit card.')
        return self
