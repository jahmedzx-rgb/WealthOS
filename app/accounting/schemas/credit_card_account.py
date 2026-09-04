from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class CreditCardAccountRequest(BaseModel):
    issuer_bank: str = Field(min_length=1, max_length=120)
    card_name: str = Field(min_length=1, max_length=120)
    last4: str = Field(pattern=r"^\d{4}$")
    credit_limit: Decimal = Field(gt=0)
    used_balance: Decimal = Field(default=0, ge=0)
    statement_balance: Decimal | None = Field(default=None, ge=0)
    minimum_monthly_payment: Decimal = Field(default=0, ge=0)
    statement_balance: Decimal = Field(default=0, ge=0)
    statement_cutoff_day: int = Field(ge=1, le=31)
    payment_due_day: int = Field(ge=1, le=31)
    is_fee_free: bool = False
    annual_fee: Decimal = Field(default=0, ge=0)
    fee_renewal_day: int | None = Field(default=None, ge=1, le=31)
    fee_renewal_month: int | None = Field(default=None, ge=1, le=12)
    currency_code: str = Field(default="SAR", min_length=3, max_length=3)
    as_of_date: datetime


class CreditCardUpdateRequest(BaseModel):
    issuer_bank: str = Field(min_length=1, max_length=120)
    card_name: str = Field(min_length=1, max_length=120)
    last4: str = Field(pattern=r"^\d{4}$")
    credit_limit: Decimal = Field(gt=0)
    minimum_monthly_payment: Decimal = Field(default=0, ge=0)
    statement_cutoff_day: int = Field(ge=1, le=31)
    payment_due_day: int = Field(ge=1, le=31)
    currency_code: str = Field(min_length=3, max_length=3)
    is_fee_free: bool = False
    annual_fee: Decimal = Field(default=0, ge=0)
    fee_renewal_day: int | None = Field(default=None, ge=1, le=31)
    fee_renewal_month: int | None = Field(default=None, ge=1, le=12)


class CreditCardBalanceAdjustmentRequest(BaseModel):
    corrected_balance: Decimal = Field(ge=0)
    adjustment_date: datetime
    reason: str = Field(min_length=3, max_length=240)
