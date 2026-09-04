from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PropertyUpdateRequest(BaseModel):
    property_name: str = Field(..., min_length=1, max_length=160)
    property_usage: str = Field(pattern="^(PRIMARY_RESIDENCE|INVESTMENT_PROPERTY|VACATION_HOME|OTHER)$")
    property_income_type: str | None = Field(default=None, pattern="^(RESIDENTIAL_RENT|COMMERCIAL_RENT|SHORT_TERM_RENT)$")


class PropertyValueAdjustmentRequest(BaseModel):
    corrected_value: Decimal = Field(..., ge=0)
    adjustment_date: datetime
    reason: str = Field(..., min_length=3, max_length=255)
