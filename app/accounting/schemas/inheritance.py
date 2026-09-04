from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class InheritanceRequest(BaseModel):
    timing: str = Field(pattern="^(BEFORE_WEALTHOS|RECEIVED_AFTER_START)$")
    asset_type: str = Field(pattern="^(CASH_ON_HAND|BANK_ACCOUNT|PROPERTY|VEHICLE|INVESTMENT|OTHER_ASSET)$")
    amount: Decimal = Field(gt=0)
    transaction_date: datetime
    description: str = Field(min_length=3, max_length=255)
    asset_name: str | None = Field(default=None, max_length=160)
    bank_account_id: int | None = Field(default=None, gt=0)
    property_usage: str | None = Field(default=None, pattern="^(PRIMARY_RESIDENCE|INVESTMENT_PROPERTY|VACATION_HOME|OTHER)$")
    property_income_type: str | None = Field(default=None, pattern="^(RESIDENTIAL_RENT|COMMERCIAL_RENT|SHORT_TERM_RENT)$")

    @model_validator(mode="after")
    def validate_asset_details(self):
        if self.asset_type == "BANK_ACCOUNT" and self.bank_account_id is None:
            raise ValueError("Select the bank account receiving the inherited money.")
        if self.asset_type == "PROPERTY":
            if not self.asset_name or not self.property_usage:
                raise ValueError("Enter the inherited property name and use.")
            if self.property_usage == "INVESTMENT_PROPERTY" and self.property_income_type is None:
                raise ValueError("Select the real estate income type for the inherited investment property.")
        if self.asset_type not in {"CASH_ON_HAND", "BANK_ACCOUNT"} and not self.asset_name:
            raise ValueError("Enter a name for the inherited asset.")
        return self
