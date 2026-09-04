import re


def normalize_bank_account_identifier(value: str) -> str:
    """Return the canonical comparison form without exposing it in logs."""
    return re.sub(r"[\s\-]+", "", value).upper()


def mask_bank_account_identifier(value: str) -> str:
    normalized = normalize_bank_account_identifier(value)
    return f"•• {normalized[-4:]}"
