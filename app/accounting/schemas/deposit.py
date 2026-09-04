from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class DepositRequest(BaseModel):
    provider_name: str = Field(min_length=1, max_length=120)
    product_name: str = Field(min_length=1, max_length=120)
    product_type: str = Field(pattern="^(TERM_DEPOSIT|INCOME_SAVINGS)$")
    funding_bank_account_id: int = Field(gt=0)
    income_bank_account_id: int | None = Field(default=None, gt=0)
    principal_amount: Decimal = Field(gt=0)
    annual_return_rate: Decimal = Field(ge=0, le=100)
    payout_frequency: str = Field(pattern="^(MONTHLY|QUARTERLY|AT_MATURITY)$")
    start_date: date
    maturity_date: date | None = None
    auto_renew: bool = False
    currency_code: str = Field(min_length=3, max_length=3)
    transaction_date: datetime

    @model_validator(mode="after")
    def validate_dates(self):
        if self.product_type == "TERM_DEPOSIT" and self.maturity_date is None:
            raise ValueError("Maturity date is required for a term deposit.")
        if self.maturity_date is not None and self.maturity_date <= self.start_date:
            raise ValueError("Maturity date must be after the start date.")
        return self


class DepositUpdateRequest(BaseModel):
    provider_name: str = Field(min_length=1, max_length=120)
    product_name: str = Field(min_length=1, max_length=120)
    product_type: str = Field(pattern="^(TERM_DEPOSIT|INCOME_SAVINGS)$")
    income_bank_account_id: int | None = Field(default=None, gt=0)
    annual_return_rate: Decimal = Field(ge=0, le=100)
    payout_frequency: str = Field(pattern="^(MONTHLY|QUARTERLY|AT_MATURITY)$")
    start_date: date
    maturity_date: date | None = None
    auto_renew: bool = False

    @model_validator(mode="after")
    def validate_dates(self):
        if self.product_type == "TERM_DEPOSIT" and self.maturity_date is None:
            raise ValueError("Maturity date is required for a term deposit.")
        if self.maturity_date is not None and self.maturity_date <= self.start_date:
            raise ValueError("Maturity date must be after the start date.")
        return self


class DepositBalanceAdjustmentRequest(BaseModel):
    corrected_balance: Decimal = Field(ge=0)
    adjustment_date: datetime
    reason: str = Field(min_length=3, max_length=240)
