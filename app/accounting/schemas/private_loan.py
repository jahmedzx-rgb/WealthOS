from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class PrivateLoanRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    lender: str = Field(min_length=2, max_length=120)
    mode: Literal['OPENING', 'BANK', 'DIRECT_EXPENSE']
    principal: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    agreed_extra: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=2)
    prior_paid: Decimal = Field(default=Decimal('0'), ge=0, max_digits=18, decimal_places=2)
    record_date: date
    bank_account_id: int | None = Field(default=None, gt=0)
    expense_account_code: int | None = Field(default=None, gt=0)
    beneficiary: str = Field(default='', max_length=120)
    note: str = Field(default='', max_length=500)
    idempotency_key: str = Field(min_length=16, max_length=100)

    @model_validator(mode='after')
    def valid_mode(self):
        if not self.name.strip() or not self.lender.strip():
            raise ValueError('Name and lender are required.')
        if self.prior_paid >= self.principal + self.agreed_extra:
            raise ValueError('Prior payments must be less than the total obligation.')
        if self.mode != 'OPENING' and self.prior_paid:
            raise ValueError('Prior payments are only allowed for an opening loan.')
        if self.mode == 'BANK' and not self.bank_account_id:
            raise ValueError('Select a destination bank account.')
        if self.mode != 'BANK' and self.bank_account_id:
            raise ValueError('This mode must not change a destination bank account.')
        if self.mode == 'DIRECT_EXPENSE' and (not self.expense_account_code or not self.beneficiary.strip()):
            raise ValueError('Select the expense account and beneficiary.')
        if self.mode != 'DIRECT_EXPENSE' and (self.expense_account_code or self.beneficiary):
            raise ValueError('Direct payment details are not allowed for this mode.')
        return self

class PrivateLoanPaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    payment_date: date
    mode: Literal['BANK', 'HISTORICAL'] = 'BANK'
    bank_account_id: int | None = Field(default=None, gt=0)
    historical_source: str = Field(default='', max_length=160)
    note: str = Field(default='', max_length=500)
    idempotency_key: str = Field(min_length=16, max_length=100)

    @model_validator(mode='after')
    def valid_source(self):
        if self.mode == 'BANK' and not self.bank_account_id:
            raise ValueError('Select the bank account used for payment.')
        if self.mode == 'HISTORICAL' and not self.historical_source.strip():
            raise ValueError('Describe the historical payment source.')
        if self.mode == 'HISTORICAL' and self.bank_account_id:
            raise ValueError('A historical payment must not change a current bank balance.')
        return self

class PrivateLoanUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    lender: str = Field(min_length=2, max_length=120)
    note: str = Field(default='', max_length=500)

class PrivateLoanPriorPaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    payment_date: date
    source: str = Field(min_length=2, max_length=160)
    note: str = Field(default='', max_length=500)
    idempotency_key: str = Field(min_length=16, max_length=100)

class PrivateLoanPriorPaymentItem(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    payment_date: date
    source: str = Field(min_length=2, max_length=160)
    note: str = Field(default='', max_length=500)

class PrivateLoanPriorPaymentBulkRequest(BaseModel):
    items: list[PrivateLoanPriorPaymentItem] = Field(min_length=1, max_length=20)
    idempotency_key: str = Field(min_length=16, max_length=80)
