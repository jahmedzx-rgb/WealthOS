from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class SavingCircleRequest(BaseModel):
    platform_name: str = Field(min_length=2, max_length=120)
    circle_name: str = Field(min_length=2, max_length=140)
    installment_amount: Decimal = Field(gt=0)
    frequency: str = Field(pattern="^(WEEKLY|MONTHLY)$")
    total_installments: int = Field(ge=2, le=120)
    payout_installment: int = Field(ge=1, le=120)
    installments_paid: int = Field(default=0, ge=0, le=120)
    start_date: date
    next_payment_date: date | None = None
    payout_date: date | None = None
    funding_bank_account_id: int = Field(gt=0)
    transaction_date: datetime

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.payout_installment > self.total_installments:
            raise ValueError("Payout installment cannot exceed total installments.")
        if self.installments_paid > self.total_installments:
            raise ValueError("Paid installments cannot exceed total installments.")
        return self


class AlternativeInvestmentRequest(BaseModel):
    recording_method: str = Field(default="BANK", pattern="^(BANK|OPENING)$")
    platform_name: str = Field(min_length=2, max_length=120)
    investment_name: str = Field(min_length=2, max_length=160)
    investment_type: str = Field(pattern="^(DEBT_CROWDFUNDING|PRIVATE_FUND|EQUITY_CROWDFUNDING|REAL_ESTATE_CROWDFUNDING|P2P_LENDING|PRIVATE_EQUITY|VENTURE_CAPITAL|PRIVATE_SUKUK|MANAGED_PORTFOLIO|OTHER)$")
    funding_bank_account_id: int | None = Field(default=None, gt=0)
    principal_amount: Decimal = Field(gt=0)
    current_value: Decimal | None = Field(default=None, gt=0)
    expected_annual_return: Decimal = Field(default=0, ge=0, le=100)
    investment_date: date
    maturity_date: date | None = None
    next_distribution_date: date | None = None
    distribution_frequency: str | None = Field(default=None, pattern="^(WEEKLY|MONTHLY|QUARTERLY|SEMI_ANNUAL|ANNUAL|AT_MATURITY)$")
    currency_code: str = Field(default="SAR", min_length=3, max_length=3)
    transaction_date: datetime
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_funding(self):
        if self.recording_method == "BANK" and self.funding_bank_account_id is None:
            raise ValueError("Funding bank account is required for a bank-funded investment.")
        if self.recording_method == "BANK" and self.current_value not in (None, self.principal_amount):
            raise ValueError("A newly funded investment starts at its principal amount.")
        return self
