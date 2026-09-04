from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database.model_registry  # noqa: F401
from app.accounting.bank_identifiers import mask_bank_account_identifier, normalize_bank_account_identifier
from app.accounting.models import Account, BankAccount, BankAccountIdentifierAudit
from app.accounting.schemas.bank_account import BankAccountRequest, BankAccountUpdateRequest
from app.api.v1.accounting import (
    bank_account_duplicate_report,
    create_bank_account,
    get_bank_account,
    list_bank_accounts,
    update_bank_account,
)
from app.core.models.user import User
from app.database.base import Base


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id=1, email="bank-identifiers@example.com", full_name="Bank Identifier Test")
    bank_ledger = Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT")
    db.add_all([user, bank_ledger])
    db.commit()
    return db, user


def request(identifier: str, *, bank_name: str = "Example Bank") -> BankAccountRequest:
    return BankAccountRequest(
        bank_name=bank_name,
        account_type="CURRENT",
        account_name="Primary",
        account_identifier=identifier,
        currency_code="SAR",
        opening_balance=Decimal("0"),
        as_of_date=datetime.now(UTC),
    )


def test_normalizes_spaces_hyphens_and_case():
    assert normalize_bank_account_identifier(" sa12-3456 7890 ") == "SA1234567890"


def test_mask_exposes_only_last_four_characters():
    masked = mask_bank_account_identifier("SA12-3456-7890")
    assert masked == "•• 7890"
    assert "SA12" not in masked


def test_create_normalizes_and_masks_response_and_lists():
    db, user = make_db()

    created = create_bank_account(request(" sa12-3456 7890 "), db, user)

    assert created["account_identifier"] == "•• 7890"
    assert created["display_name"] == "Example Bank •• 7890"
    stored = db.query(BankAccount).one()
    assert stored.account_identifier == "SA1234567890"
    assert stored.account_identifier_normalized == "SA1234567890"
    assert list_bank_accounts(db, user)[0]["account_identifier"] == "•• 7890"
    assert get_bank_account(stored.id, db, user)["account_identifier"] == "SA1234567890"


def test_duplicate_create_is_rejected_after_normalization():
    db, user = make_db()
    create_bank_account(request("SA12 3456-7890"), db, user)

    with pytest.raises(HTTPException) as exc_info:
        create_bank_account(request("sa1234567890", bank_name="Other Bank"), db, user)

    assert exc_info.value.status_code == 409
    assert db.query(BankAccount).count() == 1


def test_update_keeps_identity_and_records_only_masked_audit_values():
    db, user = make_db()
    create_bank_account(request("SA1234567890"), db, user)
    account = db.query(BankAccount).one()
    original_id = account.id

    updated = update_bank_account(
        original_id,
        BankAccountUpdateRequest(
            bank_name="Example Bank",
            account_type="CURRENT",
            account_name="Primary",
            account_identifier="SA98-7654-3210",
            correction_reason="Corrected account number",
        ),
        db,
        user,
    )

    assert updated["id"] == original_id
    assert db.query(BankAccount).count() == 1
    audit = db.query(BankAccountIdentifierAudit).one()
    assert (audit.previous_last4, audit.new_last4) == ("7890", "3210")
    assert "SA12" not in audit.previous_last4
    assert "SA98" not in audit.new_last4


def test_historical_duplicate_report_is_masked_and_non_destructive():
    db, user = make_db()
    db.add_all(
        [
            BankAccount(user_id=user.id, bank_name="One", account_type="CURRENT", account_name="One", account_identifier="SA12-3456", account_identifier_normalized=None, current_balance=0, currency_code="SAR"),
            BankAccount(user_id=user.id, bank_name="Two", account_type="CURRENT", account_name="Two", account_identifier="sa12 3456", account_identifier_normalized=None, current_balance=0, currency_code="SAR"),
        ]
    )
    db.commit()

    report = bank_account_duplicate_report(db, user)

    assert report == [{"masked_identifier": "•• 3456", "account_ids": [1, 2], "count": 2}]
    assert db.query(BankAccount).count() == 2
