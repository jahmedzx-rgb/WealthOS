from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Literal


class ImportedOperationInput(BaseModel):
    operation_type: str
    description: str
    amount: Decimal | None = None
    currency: str | None = None
    transaction_date: str | None = None
    card_last4: str | None = Field(default=None, pattern=r"^\d{4}$")
    confidence: int = Field(ge=0, le=100)
    source_text: str
    status: Literal["PENDING", "IGNORED"] = "PENDING"


class ImportBatchInput(BaseModel):
    filename: str
    file_size: int = Field(ge=0)
    file_type: str = ""
    operations: list[ImportedOperationInput]


class ImportedOperationConfirmation(BaseModel):
    posting_reference: str = Field(min_length=3, max_length=120)
    matched_entity_type: str | None = Field(default=None, max_length=40)
    matched_entity_id: int | None = Field(default=None, gt=0)
