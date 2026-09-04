from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator


class BreakDepositRequest(BaseModel):
    destination_bank_account_id: int = Field(..., gt=0)
    amount_received: Decimal = Field(..., ge=0)
    transaction_date: datetime
    reason: str = Field(default="Early deposit closure", min_length=3, max_length=255)


class SellPropertyRequest(BaseModel):
    payment_method: str = Field(default="BANK_TRANSFER", pattern="^(BANK_TRANSFER|CHEQUE|CASH)$")
    payment_destination: str = Field(pattern="^(BANK_ACCOUNT|CASH_ON_HAND)$")
    bank_account_id: int | None = Field(default=None, gt=0)
    sale_amount: Decimal = Field(..., gt=0)
    selling_costs: Decimal = Field(default=0, ge=0)
    transaction_date: datetime
    description: str = Field(default="Property sale", min_length=3, max_length=255)

    @model_validator(mode="after")
    def validate_destination(self):
        if self.payment_method == "BANK_TRANSFER" and self.payment_destination != "BANK_ACCOUNT":
            raise ValueError("A bank transfer must be deposited into a bank account.")
        if self.payment_method == "CASH" and self.payment_destination != "CASH_ON_HAND":
            raise ValueError("A cash sale must be received as Cash On Hand.")
        if self.payment_destination == "BANK_ACCOUNT" and self.bank_account_id is None:
            raise ValueError("Select the bank account receiving the sale proceeds.")
        if self.selling_costs >= self.sale_amount:
            raise ValueError("Selling costs must be lower than the sale amount.")
        return self
