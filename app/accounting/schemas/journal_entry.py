from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class JournalEntryLineRequest(BaseModel):
    account_code: int = Field(
        ...,
        gt=0,
    )

    debit: Decimal = Field(
        default=0,
        ge=0,
    )

    credit: Decimal = Field(
        default=0,
        ge=0,
    )


class JournalEntryRequest(BaseModel):
    transaction_date: datetime

    related_reference: str | None = Field(
        default=None,
        max_length=200,
    )

    description: str = Field(
        ...,
        max_length=255,
    )

    lines: list[JournalEntryLineRequest] = Field(
        min_length=2,
    )
