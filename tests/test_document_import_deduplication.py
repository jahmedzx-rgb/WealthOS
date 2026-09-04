from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database.model_registry  # noqa: F401
from app.api.v1.document_imports import delete_batch, save_batch
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
