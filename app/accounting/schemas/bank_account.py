from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class BankAccountRequest(BaseModel):
    bank_name: str = Field(min_length=1, max_length=120)
    account_type: str = Field(min_length=1, max_length=40)
    account_name: str | None = Field(default=None, max_length=120)
    account_identifier: str = Field(min_length=4, max_length=64)
    currency_code: str = Field(default="SAR", min_length=3, max_length=3)
    opening_balance: Decimal = Field(default=0)
    as_of_date: datetime
    is_primary: bool = False


class BankOpeningBalanceRequest(BaseModel):
    corrected_opening_balance: Decimal = Field(ge=0)
    opening_date: datetime
    adjustment_date: datetime
    reason: str = Field(min_length=3, max_length=255)


class BankAccountUpdateRequest(BaseModel):
    bank_name: str = Field(min_length=1, max_length=120)
    account_type: str = Field(min_length=1, max_length=40)
    account_name: str | None = Field(default=None, max_length=120)
    account_identifier: str = Field(min_length=4, max_length=64)
    correction_reason: str = Field(min_length=3, max_length=255)
