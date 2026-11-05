from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database.model_registry  # noqa: F401
from app.api.v1.document_imports import delete_batch, pending_batches, save_batch
from app.core.models.user import User
from app.database.base import Base
from app.document_imports.models import ImportBatch, ImportedOperation
from app.document_imports.schemas import ImportBatchInput, ImportedOperationInput


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def operation(source_text: str, amount: str = "961.67"):
    return ImportedOperationInput(operation_type="Trade", description=source_text, amount=Decimal(amount), transaction_date="03/03/2026", confidence=90, source_text=source_text)


def test_reimported_confirmed_operation_is_marked_duplicate():
    db = make_db()
    user = User(email="dedupe@example.com", full_name="Dedupe Test")
    db.add(user)
    db.commit()
    source = "2 | 03/03/2026 | شراء | السهم 4002 | 20260303013068 | 961.67 | | 39.16"
    first = save_batch(ImportBatchInput(filename="first.xls", file_size=10, operations=[operation(source)]), db, user)
    original = db.get(ImportedOperation, first["operations"][0]["id"])
    original.status = "CONFIRMED"
    original.posting_reference = "trade:42"
    db.commit()

    second = save_batch(ImportBatchInput(filename="renamed.xls", file_size=10, operations=[operation(source)]), db, user)

    assert second["status"] == "COMPLETED"
    assert second["operations"][0]["status"] == "DUPLICATE"
    assert second["operations"][0]["posting_reference"] == "trade:42"


def test_sms_reimport_refreshes_pending_operation_time_without_duplicate():
    db = make_db()
    user = User(email="sms-refresh@example.com", full_name="SMS Refresh Test")
    db.add(user)
    db.commit()
    old_source = "2026-09-25 | NEO | Purchase at Example Store for SAR 18.50"
    first = save_batch(
        ImportBatchInput(filename="sms-backup.xml", file_size=100, file_type="application/xml", operations=[
            ImportedOperationInput(operation_type="Expense", description=old_source, amount=Decimal("18.50"), transaction_date="2026-09-25", confidence=70, source_text=old_source),
        ]), db, user,
    )
    original_id = first["operations"][0]["id"]

    new_source = "2026-09-25T16:37 | NEO | Purchase at Example Store for SAR 18.50"
    refreshed = save_batch(
        ImportBatchInput(filename="sms-backup-new.xml", file_size=120, file_type="application/xml", operations=[
            ImportedOperationInput(operation_type="Expense", description=new_source, amount=Decimal("18.50"), transaction_date="2026-09-25T16:37", confidence=90, source_text=new_source),
        ]), db, user,
    )

    assert refreshed["operations"][0]["id"] == original_id
    assert refreshed["operations"][0]["transaction_date"] == "2026-09-25T16:37"
    assert refreshed["operations"][0]["source_text"] == new_source
    assert refreshed["filename"] == "sms-backup-new.xml"
    assert db.get(ImportedOperation, original_id).batch_id == refreshed["id"]
    assert db.query(ImportBatch).filter(ImportBatch.user_id == user.id).count() == 2
    assert db.get(ImportBatch, first["id"]).status == "COMPLETED"
    assert db.query(ImportedOperation).filter(ImportedOperation.status == "PENDING").count() == 1
    queue = pending_batches(db, user)
    assert [batch["id"] for batch in queue] == [refreshed["id"]]
    assert [item["id"] for item in queue[0]["operations"]] == [original_id]


def test_reimport_refreshes_repeated_identical_sms_one_at_a_time():
    db = make_db()
    user = User(email="sms-repeat@example.com", full_name="SMS Repeat Test")
    db.add(user)
    db.commit()
    old_source = "2026-09-25 | NEO | Purchase at Example Store for SAR 18.50"
    first = save_batch(
        ImportBatchInput(filename="sms-backup.xml", file_size=100, file_type="application/xml", operations=[
            ImportedOperationInput(operation_type="Expense", description=old_source, amount=Decimal("18.50"), transaction_date="2026-09-25", confidence=70, source_text=old_source),
            ImportedOperationInput(operation_type="Expense", description=old_source, amount=Decimal("18.50"), transaction_date="2026-09-25", confidence=70, source_text=old_source),
        ]), db, user,
    )
    old_ids = [item["id"] for item in first["operations"]]
    new_sources = [
        "2026-09-25T16:37 | NEO | Purchase at Example Store for SAR 18.50",
        "2026-09-25T18:12 | NEO | Purchase at Example Store for SAR 18.50",
    ]
    refreshed = save_batch(
        ImportBatchInput(filename="sms-backup-new.xml", file_size=120, file_type="application/xml", operations=[
            ImportedOperationInput(operation_type="Expense", description=source, amount=Decimal("18.50"), transaction_date=source.split(" | ")[0], confidence=90, source_text=source)
            for source in new_sources
        ]), db, user,
    )

    assert {item["id"] for item in refreshed["operations"]} == set(old_ids)
    assert [item["transaction_date"] for item in refreshed["operations"]] == ["2026-09-25T16:37", "2026-09-25T18:12"]
    assert {db.get(ImportedOperation, item_id).batch_id for item_id in old_ids} == {refreshed["id"]}
    assert db.get(ImportBatch, first["id"]).status == "COMPLETED"
    assert db.query(ImportedOperation).filter(ImportedOperation.status == "PENDING").count() == 2


def test_reimport_after_deleting_old_sms_file_restores_operation_in_new_file():
    db = make_db()
    user = User(email="sms-delete-reimport@example.com", full_name="SMS Delete Reimport Test")
    db.add(user)
    db.commit()
    source = "2026-09-25 | NEO | Purchase at Example Store for SAR 18.50"
    first = save_batch(
        ImportBatchInput(filename="sms-backup.xml", file_size=100, file_type="application/xml", operations=[
            ImportedOperationInput(operation_type="Expense", description=source, amount=Decimal("18.50"), transaction_date="2026-09-25", confidence=70, source_text=source),
        ]), db, user,
    )

    delete_batch(first["id"], db, user)
    assert db.get(ImportBatch, first["id"]) is None

    refreshed_source = "2026-09-25T16:37 | NEO | Purchase at Example Store for SAR 18.50"
    reimported = save_batch(
        ImportBatchInput(filename="sms-backup-again.xml", file_size=120, file_type="application/xml", operations=[
            ImportedOperationInput(operation_type="Expense", description=refreshed_source, amount=Decimal("18.50"), transaction_date="2026-09-25T16:37", confidence=90, source_text=refreshed_source),
        ]), db, user,
    )

    assert reimported["filename"] == "sms-backup-again.xml"
    assert reimported["operations"][0]["status"] == "PENDING"
    assert reimported["operations"][0]["transaction_date"] == "2026-09-25T16:37"
    assert len(pending_batches(db, user)) == 1
    assert len(pending_batches(db, user)[0]["operations"]) == 1


def test_delete_hides_file_but_preserves_confirmed_audit_record():
    db = make_db()
    user = User(email="remove@example.com", full_name="Remove Test")
    db.add(user)
    db.commit()
    batch = ImportBatch(user_id=user.id, filename="statement.xls", file_size=10, file_type="application/vnd.ms-excel")
    batch.operations = [
        ImportedOperation(operation_type="Trade", description="posted", amount=Decimal("10"), confidence=90, source_text="posted", status="CONFIRMED", posting_reference="trade:1"),
        ImportedOperation(operation_type="Transfer", description="draft", amount=Decimal("20"), confidence=90, source_text="draft", status="PENDING"),
    ]
    db.add(batch)
    db.commit()
    batch_id = batch.id
    confirmed_id = batch.operations[0].id

    delete_batch(batch_id, db, user)

    assert db.get(ImportBatch, batch_id).status == "REMOVED"
    assert db.get(ImportedOperation, confirmed_id) is not None
    assert db.query(ImportedOperation).filter(ImportedOperation.batch_id == batch_id).count() == 1
