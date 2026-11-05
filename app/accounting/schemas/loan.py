from datetime import date
from decimal import Decimal

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class LoanRequest(BaseModel):
    recording_method: Literal["BANK", "OPENING"] = "BANK"
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
    payment_day: int | None = Field(default=None, ge=1, le=31)
    destination_account_code: int = Field(default=1120, gt=0)
    destination_bank_account_id: int | None = Field(default=None, gt=0)
    payment_bank_account_id: int | None = Field(default=None, gt=0)
    remaining_installments: int | None = Field(default=None, gt=0, le=600)
    current_outstanding_balance: Decimal | None = Field(default=None, gt=0)
    early_settlement_amount: Decimal | None = Field(default=None, gt=0)
    bank_balance_adjustment: Decimal = Field(default=Decimal("0.00"), ge=Decimal("-1.00"), le=Decimal("1.00"))
    opening_balance_date: date | None = None

    @model_validator(mode="after")
    def validate_funding(self):
        if self.payment_day is None:
            self.payment_day = self.first_payment_date.day
        if self.amount_received + self.fees != self.principal_amount:
            raise ValueError("Amount received plus fees must equal the principal amount.")
        if self.recording_method == "BANK" and not self.destination_bank_account_id:
            raise ValueError("Select a destination bank account.")
        if self.payment_bank_account_id is None:
            self.payment_bank_account_id = self.destination_bank_account_id
        if self.recording_method == "OPENING":
            if self.remaining_installments is None or self.opening_balance_date is None:
                raise ValueError("Remaining installments and opening balance date are required.")
            calculated_balance = self.current_outstanding_balance or (self.monthly_payment * self.remaining_installments + self.bank_balance_adjustment)
            if calculated_balance <= 0:
                raise ValueError("The current outstanding balance must be greater than zero.")
            if calculated_balance > self.principal_amount:
                raise ValueError("The opening balance cannot exceed the original principal amount.")
            if self.early_settlement_amount is not None and self.early_settlement_amount > calculated_balance:
                raise ValueError("The early settlement amount cannot exceed the current outstanding balance.")
            if self.remaining_installments > self.term_months:
                raise ValueError("Remaining installments cannot exceed the original term.")
        return self


class LoanUpdateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    lender: str = Field(..., min_length=2, max_length=120)
    annual_rate: Decimal = Field(..., ge=0, le=100)
    term_months: int = Field(..., gt=0, le=600)
    monthly_payment: Decimal = Field(..., gt=0)
    first_payment_date: date
    payment_day: int | None = Field(default=None, ge=1, le=31)
    payment_bank_account_id: int | None = Field(default=None, gt=0)


class LoanSettlementRequest(BaseModel):
    settlement_amount: Decimal = Field(..., gt=0)
    payment_account_code: int = Field(default=1120, gt=0)
    payment_bank_account_id: int = Field(..., gt=0)


class LoanPaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    payment_date: date
    payment_bank_account_id: int = Field(..., gt=0)
    idempotency_key: str = Field(..., min_length=8, max_length=100)
    note: str = Field(default="", max_length=500)


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
