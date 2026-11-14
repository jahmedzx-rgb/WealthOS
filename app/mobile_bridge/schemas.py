from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PairingCreate(BaseModel):
    sender_allowlist: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("sender_allowlist")
    @classmethod
    def clean_senders(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class PairingClaim(BaseModel):
    pairing_secret: str = Field(min_length=32, max_length=180)
    device_name: str = Field(min_length=2, max_length=120)
    installation_id: str = Field(min_length=8, max_length=120)
    app_version: str | None = Field(default=None, max_length=40)
    os_version: str | None = Field(default=None, max_length=40)


class MobileMessageInput(BaseModel):
    source_id: str = Field(min_length=1, max_length=160)
    sender: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)
    received_at: datetime


class MobileMessageBatch(BaseModel):
    messages: list[MobileMessageInput] = Field(min_length=1, max_length=500)
    history_sync: bool = False


class DeviceSenderUpdate(BaseModel):
    sender_allowlist: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("sender_allowlist")
    @classmethod
    def clean_senders(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))
