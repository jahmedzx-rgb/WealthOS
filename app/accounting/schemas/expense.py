from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ExpenseRequest(BaseModel):
    expense_account_code: int = Field(..., gt=0)
    payment_bank_account_id: int = Field(..., gt=0)
    property_id: int | None = Field(default=None, gt=0)
    amount: Decimal = Field(..., gt=0)
    transaction_date: datetime
    description: str = Field(..., min_length=1, max_length=255)
