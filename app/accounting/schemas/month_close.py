from pydantic import BaseModel, Field


class MonthCloseRequest(BaseModel):
    year: int = Field(..., ge=2000, le=2200)
    month: int = Field(..., ge=1, le=12)


class MonthReopenRequest(BaseModel):
    reason: str = Field(..., min_length=8, max_length=500)
