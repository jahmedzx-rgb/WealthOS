from pydantic import BaseModel, Field, field_validator


class SaudiSecurityRequest(BaseModel):
    symbol: str = Field(min_length=4, max_length=4)
    name: str = Field(min_length=2, max_length=200)
    security_type: str = Field(default="STOCK", pattern="^(STOCK|ETF|REIT)$")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.isdigit():
            raise ValueError("Saudi Exchange symbol must contain exactly four digits.")
        return normalized

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()


class MarketSecurityRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    market_symbol: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=2, max_length=200)
    security_type: str = Field(pattern="^(STOCK|ETF|REIT)$")
    exchange: str = Field(min_length=2, max_length=50)
    currency_code: str = Field(default="", max_length=3)

    @field_validator("symbol", "market_symbol", "exchange", "currency_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()
