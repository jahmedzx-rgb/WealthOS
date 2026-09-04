from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class BrokerRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    country: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=255)
    commission_rate: Decimal | None = Field(default=None, ge=0, le=100)
    commission_tax_rate: Decimal | None = Field(default=None, ge=0, le=100)
    dividend_withholding_tax_rate: Decimal | None = Field(default=None, ge=0, le=100)
    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("country", "website")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class BrokerCommissionRequest(BaseModel):
    commission_rate: Decimal = Field(ge=0, le=100)
    commission_tax_rate: Decimal = Field(ge=0, le=100)
    dividend_withholding_tax_rate: Decimal | None = Field(default=None, ge=0, le=100)
    website: str | None = Field(default=None, max_length=255)

    @field_validator("website")
    @classmethod
    def clean_website(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
