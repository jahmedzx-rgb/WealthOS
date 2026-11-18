from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

import app.database.model_registry  # noqa: F401
from app.api.v1.mobile_bridge import claim_pairing, create_pairing, ingest_messages
from app.core.models.user import User
from app.database.base import Base
from app.document_imports.models import ImportedOperation
from app.mobile_bridge.models import MobileDevice, MobileMessage
from app.mobile_bridge.parser import parse_financial_message
from app.mobile_bridge.schemas import MobileMessageBatch, MobileMessageInput, PairingClaim, PairingCreate


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def request():
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": ("127.0.0.1", 9000)})


def test_arabic_bank_message_is_parsed_without_otp_content():
    parsed = parse_financial_message("SNB", "شراء عن طريق نقاط البيع بمبلغ ١٢٣٫٤٥ ر.س بطاقة مدى **7304", datetime(2026, 10, 20, 12, tzinfo=UTC))
    assert parsed is not None
    assert parsed.operation_type == "Expense"
    assert str(parsed.amount) == "123.45"
    assert parsed.currency == "SAR"
    assert parsed.card_last4 == "7304"
    assert parse_financial_message("SNB", "رمز التحقق 1234 لا تشاركه", datetime.now(UTC)) is None


def test_pairing_and_ingestion_create_one_review_operation_and_dedupe():
    db = make_db()
    user = User(email="mobile@example.com", full_name="Mobile Test", is_active=True)
    db.add(user)
    db.commit()
    pairing = create_pairing(PairingCreate(sender_allowlist=[]), db, user)
    claimed = claim_pairing(PairingClaim(
        pairing_secret=pairing["pairing_secret"],
        device_name="Ahmed Phone",
        installation_id="installation-123",
        app_version="0.1.0",
        os_version="Android 16",
    ), request(), db)
    device = db.query(MobileDevice).filter_by(public_id=claimed["device_id"]).one()
    message = MobileMessageInput(
        source_id="sms-42",
        sender="SNB",
        body="Purchase amount SAR 48.75 using card **7304",
        received_at=datetime(2026, 10, 20, 12, tzinfo=UTC),
    )
    first = ingest_messages(MobileMessageBatch(messages=[message], history_sync=True), db, device)
    second = ingest_messages(MobileMessageBatch(messages=[message], history_sync=True), db, device)
    assert first["accepted"] == 1
    assert first["review_required"] is True
    assert second["accepted"] == 0
    assert second["duplicates"] == 1
    assert db.query(MobileMessage).count() == 1
    operation = db.query(ImportedOperation).one()
    assert operation.status == "PENDING"
    assert operation.amount == 48.75
    assert operation.card_last4 == "7304"


def test_built_in_abyan_trade_sender_is_accepted_for_existing_device_allowlist():
    db = make_db()
    user = User(email="abyan@example.com", full_name="Abyan Test", is_active=True)
    db.add(user)
    db.commit()
    pairing = create_pairing(PairingCreate(sender_allowlist=["SNB"]), db, user)
    claimed = claim_pairing(PairingClaim(
        pairing_secret=pairing["pairing_secret"],
        device_name="Ahmed Phone",
        installation_id="installation-abyan",
        app_version="0.2.2",
        os_version="Android 15",
    ), request(), db)
    device = db.query(MobileDevice).filter_by(public_id=claimed["device_id"]).one()
    result = ingest_messages(MobileMessageBatch(messages=[MobileMessageInput(
        source_id="abyan-trade-1",
        sender="Abyan Trade",
        body="تم تنفيذ شراء سهم بمبلغ 25.00 SAR",
        received_at=datetime(2026, 11, 18, 20, tzinfo=UTC),
    )]), db, device)
    assert result["accepted"] == 1
    operation = db.query(ImportedOperation).one()
    assert operation.operation_type == "Trade"
    assert operation.amount == 25
