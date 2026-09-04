from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class LoanRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    lender: str = Field(..., min_length=2, max_length=120)
    loan_type: str = Field(..., pattern="^(SHORT_TERM|LONG_TERM|MORTGAGE)$")
    principal_amount: Decimal = Field(..., gt=0)
    amount_received: Decimal = Field(..., gt=0)
    fees: Decimal = Field(default=Decimal("0.00"), ge=0)
    annual_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    term_months: int = Field(..., gt=0, le=600)
    monthly_payment: Decimal = Field(..., gt=0)
    first_payment_date: date
    destination_account_code: int = Field(default=1120, gt=0)
    destination_bank_account_id: int = Field(..., gt=0)

    @model_validator(mode="after")
    def validate_funding(self):
        if self.amount_received + self.fees != self.principal_amount:
            raise ValueError("Amount received plus fees must equal the principal amount.")
        return self


class LoanUpdateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    lender: str = Field(..., min_length=2, max_length=120)
    annual_rate: Decimal = Field(..., ge=0, le=100)
    term_months: int = Field(..., gt=0, le=600)
    monthly_payment: Decimal = Field(..., gt=0)
    first_payment_date: date


class LoanSettlementRequest(BaseModel):
    settlement_amount: Decimal = Field(..., gt=0)
    payment_account_code: int = Field(default=1120, gt=0)
    payment_bank_account_id: int = Field(..., gt=0)


class LoanRefinanceRequest(BaseModel):
    lender: str = Field(..., min_length=2, max_length=120)
    principal_amount: Decimal = Field(..., gt=0)
    fees: Decimal = Field(default=Decimal("0.00"), ge=0)
    annual_rate: Decimal = Field(..., ge=0, le=100)
    term_months: int = Field(..., gt=0, le=600)
    monthly_payment: Decimal = Field(..., gt=0)
    first_payment_date: date
    loan_type: str = Field(..., pattern="^(SHORT_TERM|LONG_TERM|MORTGAGE)$")
    bank_account_code: int = Field(default=1120, gt=0)
    bank_account_id: int = Field(..., gt=0)
