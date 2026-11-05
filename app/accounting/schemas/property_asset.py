from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class OpeningPropertyRequest(BaseModel):
    property_name: str = Field(min_length=1, max_length=160)
    property_usage: str = Field(pattern="^(PRIMARY_RESIDENCE|INVESTMENT_PROPERTY|VACATION_HOME|OTHER)$")
    property_income_type: str | None = Field(default=None, pattern="^(RESIDENTIAL_RENT|COMMERCIAL_RENT|SHORT_TERM_RENT)$")
    opening_date: datetime
    acquisition_date: datetime | None = None
    purchase_price: Decimal = Field(ge=0)
    improvement_cost: Decimal = Field(default=0, ge=0)
    purchase_price_estimated: bool = False
    improvement_cost_estimated: bool = False
    market_value: Decimal | None = Field(default=None, gt=0)
    market_value_date: datetime | None = None
    market_value_source: str | None = Field(default=None, max_length=160)
    market_value_note: str | None = Field(default=None, max_length=500)
    external_property_reference: str | None = Field(default=None, min_length=1, max_length=120)
    idempotency_key: str = Field(min_length=16, max_length=64, pattern="^[A-Za-z0-9._:-]+$")

    @model_validator(mode="after")
    def validate_opening_property(self):
        if self.purchase_price + self.improvement_cost <= 0:
            raise ValueError("Cost basis must be greater than zero.")
        if self.property_usage == "INVESTMENT_PROPERTY" and self.property_income_type is None:
            raise ValueError("Select the property income type.")
        if self.property_usage != "INVESTMENT_PROPERTY" and self.property_income_type is not None:
            raise ValueError("Income type is only valid for an investment property.")
        market_fields = (self.market_value_date, self.market_value_source, self.market_value_note)
        if self.market_value is None and any(value is not None for value in market_fields):
            raise ValueError("Market value details require a market value.")
        if self.market_value is not None:
            if self.market_value_date is None or not (self.market_value_source or "").strip():
                raise ValueError("Market value date and source are required.")
            if self.market_value_date.date() != self.opening_date.date():
                raise ValueError("Opening market value must be dated on the opening date.")
        if self.acquisition_date and self.acquisition_date.date() > self.opening_date.date():
            raise ValueError("Acquisition date cannot be after the opening date.")
        return self


class PropertyUpdateRequest(BaseModel):
    property_name: str = Field(..., min_length=1, max_length=160)
    property_usage: str = Field(pattern="^(PRIMARY_RESIDENCE|INVESTMENT_PROPERTY|VACATION_HOME|OTHER)$")
    property_income_type: str | None = Field(default=None, pattern="^(RESIDENTIAL_RENT|COMMERCIAL_RENT|SHORT_TERM_RENT)$")


class PropertyValueAdjustmentRequest(BaseModel):
    corrected_value: Decimal = Field(..., ge=0)
    adjustment_date: datetime
    reason: str = Field(..., min_length=3, max_length=255)
