from pydantic import BaseModel, Field, field_validator


class InvestmentPlatformRequest(BaseModel):
    code: str = Field(min_length=2, max_length=40)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()
