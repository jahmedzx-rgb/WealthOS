from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class DepositPayoutItem(BaseModel):
    payout_date: date
    amount: Decimal = Field(gt=0)


class DepositRequest(BaseModel):
    recording_method: str = Field(default="BANK", pattern="^(BANK|OPENING)$")
    provider_name: str = Field(min_length=1, max_length=120)
    product_name: str = Field(min_length=1, max_length=120)
    product_type: str = Field(pattern="^(TERM_DEPOSIT|INCOME_SAVINGS)$")
    funding_bank_account_id: int | None = Field(default=None, gt=0)
    income_bank_account_id: int | None = Field(default=None, gt=0)
    principal_amount: Decimal = Field(gt=0)
    annual_return_rate: Decimal = Field(ge=0, le=100)
    payout_frequency: str = Field(pattern="^(DAILY|MONTHLY|QUARTERLY|AT_MATURITY)$")
    payout_schedule: list[DepositPayoutItem] = Field(default_factory=list, max_length=60)
    start_date: date
    maturity_date: date | None = None
    auto_renew: bool = False
    currency_code: str = Field(min_length=3, max_length=3)
    transaction_date: datetime

    @model_validator(mode="after")
    def validate_dates(self):
        if self.recording_method == "BANK" and self.funding_bank_account_id is None:
            raise ValueError("Funding account is required for a bank-funded deposit.")
        if self.product_type == "TERM_DEPOSIT" and self.maturity_date is None:
            raise ValueError("Maturity date is required for a term deposit.")
        if self.maturity_date is not None and self.maturity_date <= self.start_date:
            raise ValueError("Maturity date must be after the start date.")
        if any(item.payout_date <= self.start_date or self.maturity_date is not None and item.payout_date > self.maturity_date for item in self.payout_schedule):
            raise ValueError("Payout dates must be after the start date and no later than maturity.")
        return self


class DepositUpdateRequest(BaseModel):
    provider_name: str = Field(min_length=1, max_length=120)
    product_name: str = Field(min_length=1, max_length=120)
    product_type: str = Field(pattern="^(TERM_DEPOSIT|INCOME_SAVINGS)$")
    income_bank_account_id: int | None = Field(default=None, gt=0)
    annual_return_rate: Decimal = Field(ge=0, le=100)
    payout_frequency: str = Field(pattern="^(DAILY|MONTHLY|QUARTERLY|AT_MATURITY)$")
    payout_schedule: list[DepositPayoutItem] = Field(default_factory=list, max_length=60)
    start_date: date
    maturity_date: date | None = None
    auto_renew: bool = False
    historical_funding_bank_account_id: int | None = Field(default=None, gt=0)
    source_loan_id: int | None = Field(default=None, gt=0)
    historical_funding_date: date | None = None
    historical_funding_amount: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_historical_funding(self):
        selected = (self.historical_funding_bank_account_id, self.source_loan_id, self.historical_funding_date, self.historical_funding_amount)
        if any(value is not None for value in selected) and not all(value is not None for value in selected):
            raise ValueError("Loan, receiving bank, and historical funding date must be selected together.")
        return self

    @model_validator(mode="after")
    def validate_dates(self):
        if self.product_type == "TERM_DEPOSIT" and self.maturity_date is None:
            raise ValueError("Maturity date is required for a term deposit.")
        if self.maturity_date is not None and self.maturity_date <= self.start_date:
            raise ValueError("Maturity date must be after the start date.")
        if any(item.payout_date <= self.start_date or self.maturity_date is not None and item.payout_date > self.maturity_date for item in self.payout_schedule):
            raise ValueError("Payout dates must be after the start date and no later than maturity.")
        return self


class DepositBalanceAdjustmentRequest(BaseModel):
    corrected_balance: Decimal = Field(ge=0)
    adjustment_date: datetime
    reason: str = Field(min_length=3, max_length=240)


class DepositReturnReconciliationRequest(BaseModel):
    confirmed_balance: Decimal = Field(gt=0)
    transaction_date: datetime


class DepositWithdrawalRequest(BaseModel):
    destination_bank_account_id: int = Field(gt=0)
    confirmed_balance: Decimal = Field(gt=0)
    amount: Decimal = Field(gt=0)
    transaction_date: datetime
    close_deposit: bool = False

    @model_validator(mode="after")
    def validate_amount(self):
        if self.amount > self.confirmed_balance:
            raise ValueError("The withdrawal cannot exceed the confirmed provider balance.")
        if self.close_deposit and self.amount != self.confirmed_balance:
            raise ValueError("Closing an income savings deposit requires withdrawing the full confirmed balance.")
        return self
