from pydantic import BaseModel, Field


class BankCardRequest(BaseModel):
    bank_account_id: int = Field(gt=0)
    card_name: str = Field(min_length=1, max_length=120)
    last4: str = Field(pattern=r"^\d{4}$")
    card_network: str = Field(min_length=1, max_length=30)
