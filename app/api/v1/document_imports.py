from datetime import UTC, datetime
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database.engine import get_db
from app.document_imports.models import ImportBatch, ImportedOperation
from app.document_imports.schemas import ImportBatchInput, ImportedOperationConfirmation
from app.api.v1.account import current_user
from app.core.models.user import User

router = APIRouter(prefix="/imports", tags=["Document imports"])


def operation_identity(item) -> tuple:
    day, source = import_source_identity(item)
    return (item.operation_type.lower(), day, source)


def import_source_identity(item) -> tuple[str, str]:
    source = re.sub(r"\s+", " ", item.source_text.strip().lower())
    cells = [cell.strip() for cell in source.split("|")]
    if cells and re.fullmatch(r"\d+", cells[0]):
        cells = cells[1:]
    if len(cells) > 1 and re.fullmatch(
        r"(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})(?:[t ]\d{1,2}:\d{2}(?::\d{2})?)?",
        cells[0],
    ):
        cells = cells[1:]
    while cells and not cells[-1]:
        cells.pop()
    if cells and re.fullmatch(r"[-+]?\d[\d,]*(?:\.\d+)?", cells[-1]):
        cells.pop()  # A statement's running balance is not part of the transaction identity.
    transaction_date = item.transaction_date or ""
    day_match = re.match(r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})", transaction_date)
    day = day_match.group(1) if day_match else transaction_date
    return day, "|".join(cells)


def reminder_is_due(value: datetime) -> bool:
    comparable = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return comparable <= datetime.now(UTC)


def serialize_batch(batch: ImportBatch, operations=None):
    selected_operations = batch.operations if operations is None else operations
    return {"id": batch.id, "filename": batch.filename, "file_size": batch.file_size, "file_type": batch.file_type, "status": batch.status, "created_at": batch.created_at, "next_reminder_at": batch.next_reminder_at, "reminder_due": reminder_is_due(batch.next_reminder_at), "operations": [{"id": item.id, "operation_type": item.operation_type, "description": item.description, "amount": float(item.amount) if item.amount is not None else None, "currency": item.currency, "transaction_date": item.transaction_date, "card_last4": item.card_last4, "confidence": item.confidence, "source_text": item.source_text, "status": item.status, "matched_entity_type": item.matched_entity_type, "matched_entity_id": item.matched_entity_id, "posting_reference": item.posting_reference, "posted_at": item.posted_at} for item in selected_operations]}


@router.post("/batches")
def save_batch(request: ImportBatchInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    confirmed = (db.query(ImportedOperation).join(ImportBatch).filter(ImportBatch.user_id == user.id, ImportedOperation.status == "CONFIRMED").all())
    confirmed_by_identity = {operation_identity(item): item for item in confirmed}
    user_batches = db.query(ImportBatch).filter(ImportBatch.user_id == user.id).all()
    user_batch_by_id = {item.id: item for item in user_batches}
    pending = (db.query(ImportedOperation).join(ImportBatch).filter(ImportBatch.user_id == user.id, ImportBatch.status != "REMOVED", ImportedOperation.status == "PENDING").order_by(ImportedOperation.id).all())
    pending_by_source = {}
    for prior in pending:
        prior_batch = user_batch_by_id.get(prior.batch_id)
        if prior_batch is None or not prior_batch.filename.lower().endswith(".xml"):
            continue
        pending_by_source.setdefault(import_source_identity(prior), []).append(prior)
    refreshed_or_new = []
    new_operations = []
    refreshed_batch_ids = set()
    batch = ImportBatch(user_id=user.id, filename=request.filename, file_size=request.file_size, file_type=request.file_type)
    db.add(batch)
    db.flush()
    for item in request.operations:
        values = item.model_dump()
        prior = confirmed_by_identity.get(operation_identity(item))
        if prior is not None:
            values.update(status="DUPLICATE", posting_reference=prior.posting_reference, matched_entity_type=prior.matched_entity_type, matched_entity_id=prior.matched_entity_id, posted_at=prior.posted_at)
            operation = ImportedOperation(**values)
            operation.batch_id = batch.id
            new_operations.append(operation)
        elif item.status == "PENDING" and pending_by_source.get(import_source_identity(item)):
            operation = pending_by_source[import_source_identity(item)].pop(0)
            for field in ("operation_type", "description", "amount", "currency", "transaction_date", "card_last4", "confidence", "source_text"):
                setattr(operation, field, values[field])
            prior_batch = user_batch_by_id.get(operation.batch_id)
            operation.batch_id = batch.id
            if prior_batch is not None and prior_batch.status != "REMOVED":
                refreshed_batch_ids.add(prior_batch.id)
        else:
            operation = ImportedOperation(**values)
            operation.batch_id = batch.id
            new_operations.append(operation)
        refreshed_or_new.append(operation)

    for operation in new_operations:
        db.add(operation)
    db.flush()
    for prior_batch_id in refreshed_batch_ids:
        pending_count = db.query(ImportedOperation).filter(
            ImportedOperation.batch_id == prior_batch_id,
            ImportedOperation.status == "PENDING",
        ).count()
        if pending_count == 0:
            prior_batch = user_batch_by_id.get(prior_batch_id)
            if prior_batch is not None:
                prior_batch.status = "COMPLETED"
    if not any(operation.status == "PENDING" for operation in refreshed_or_new):
        batch.status = "COMPLETED"
    db.commit()
    db.refresh(batch)
    return serialize_batch(batch, refreshed_or_new)


@router.get("/batches/pending")
def pending_batches(db: Session = Depends(get_db), user: User = Depends(current_user)):
    batches = db.query(ImportBatch).options(selectinload(ImportBatch.operations)).filter(ImportBatch.user_id == user.id, ImportBatch.status == "PENDING_REVIEW").order_by(ImportBatch.created_at.desc()).all()
    return [serialize_batch(batch) for batch in batches]


@router.get("/batches")
def all_batches(db: Session = Depends(get_db), user: User = Depends(current_user)):
    batches = db.query(ImportBatch).options(selectinload(ImportBatch.operations)).filter(ImportBatch.user_id == user.id, ImportBatch.status != "REMOVED").order_by(ImportBatch.created_at.desc()).all()
    return [serialize_batch(batch) for batch in batches]


@router.delete("/batches/{batch_id}", status_code=204)
def delete_batch(batch_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    batch = db.query(ImportBatch).options(selectinload(ImportBatch.operations)).filter(ImportBatch.id == batch_id, ImportBatch.user_id == user.id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="Imported document not found.")
    confirmed = [item for item in batch.operations if item.status == "CONFIRMED" or item.posting_reference]
    if confirmed:
        for item in list(batch.operations):
            if item not in confirmed:
                db.delete(item)
        batch.status = "REMOVED"
    else:
        db.delete(batch)
    db.commit()


@router.patch("/operations/{operation_id}/{status}")
def update_operation(operation_id: int, status: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if status not in {"PENDING", "IGNORED"}:
        raise HTTPException(status_code=400, detail="Unsupported review status.")
    operation = (db.query(ImportedOperation).join(ImportBatch).filter(ImportedOperation.id == operation_id, ImportBatch.user_id == user.id).first())
    if operation is None:
        raise HTTPException(status_code=404, detail="Imported operation not found.")
    operation.status = status
    db.flush()
    pending_count = db.query(ImportedOperation).filter(ImportedOperation.batch_id == operation.batch_id, ImportedOperation.status == "PENDING").count()
    if pending_count == 0:
        batch = db.get(ImportBatch, operation.batch_id)
        if batch is not None:
            batch.status = "COMPLETED"
    db.commit()
    return {"id": operation.id, "status": operation.status}


@router.post("/operations/{operation_id}/confirm")
def confirm_operation(operation_id: int, request: ImportedOperationConfirmation, db: Session = Depends(get_db), user: User = Depends(current_user)):
    operation = (db.query(ImportedOperation).join(ImportBatch).filter(ImportedOperation.id == operation_id, ImportBatch.user_id == user.id).first())
    if operation is None:
        raise HTTPException(status_code=404, detail="Imported operation not found.")
    if operation.status == "CONFIRMED":
        if operation.posting_reference == request.posting_reference:
            return {"id": operation.id, "status": operation.status, "posting_reference": operation.posting_reference}
        raise HTTPException(status_code=409, detail="This imported operation is already linked to another posted operation.")
    operation.status = "CONFIRMED"
    operation.posting_reference = request.posting_reference.strip()
    operation.matched_entity_type = request.matched_entity_type
    operation.matched_entity_id = request.matched_entity_id
    operation.posted_at = datetime.now(UTC)
    db.flush()
    pending_count = db.query(ImportedOperation).filter(ImportedOperation.batch_id == operation.batch_id, ImportedOperation.status == "PENDING").count()
    if pending_count == 0:
        batch = db.get(ImportBatch, operation.batch_id)
        if batch is not None:
            batch.status = "COMPLETED"
    db.commit()
    return {"id": operation.id, "status": operation.status, "posting_reference": operation.posting_reference}
