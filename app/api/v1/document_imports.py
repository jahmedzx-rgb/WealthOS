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
    source = re.sub(r"\s+", " ", item.source_text.strip().lower())
    cells = [cell.strip() for cell in source.split("|")]
    if len(cells) > 2:
        if re.fullmatch(r"\d+", cells[0]):
            cells = cells[1:]
        while cells and not cells[-1]:
            cells.pop()
        if cells and re.fullmatch(r"[-+]?\d[\d,]*(?:\.\d+)?", cells[-1]):
            cells.pop()  # Running balance is not part of the transaction identity.
        source = "|".join(cells)
    return (item.operation_type.lower(), item.transaction_date or "", source)


def reminder_is_due(value: datetime) -> bool:
    comparable = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return comparable <= datetime.now(UTC)


def serialize_batch(batch: ImportBatch):
    return {"id": batch.id, "filename": batch.filename, "file_size": batch.file_size, "file_type": batch.file_type, "status": batch.status, "created_at": batch.created_at, "next_reminder_at": batch.next_reminder_at, "reminder_due": reminder_is_due(batch.next_reminder_at), "operations": [{"id": item.id, "operation_type": item.operation_type, "description": item.description, "amount": float(item.amount) if item.amount is not None else None, "currency": item.currency, "transaction_date": item.transaction_date, "card_last4": item.card_last4, "confidence": item.confidence, "source_text": item.source_text, "status": item.status, "matched_entity_type": item.matched_entity_type, "matched_entity_id": item.matched_entity_id, "posting_reference": item.posting_reference, "posted_at": item.posted_at} for item in batch.operations]}


@router.post("/batches")
def save_batch(request: ImportBatchInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    batch = ImportBatch(user_id=user.id, filename=request.filename, file_size=request.file_size, file_type=request.file_type)
    db.add(batch)
    db.flush()
    confirmed = (db.query(ImportedOperation).join(ImportBatch).filter(ImportBatch.user_id == user.id, ImportedOperation.status == "CONFIRMED").all())
    confirmed_by_identity = {operation_identity(item): item for item in confirmed}
    pending_count = 0
    for item in request.operations:
        values = item.model_dump()
        prior = confirmed_by_identity.get(operation_identity(item))
        if prior is not None:
            values.update(status="DUPLICATE", posting_reference=prior.posting_reference, matched_entity_type=prior.matched_entity_type, matched_entity_id=prior.matched_entity_id, posted_at=prior.posted_at)
        elif item.status == "PENDING":
            pending_count += 1
        db.add(ImportedOperation(batch_id=batch.id, **values))
    if pending_count == 0:
        batch.status = "COMPLETED"
    db.commit()
    saved_batch = db.query(ImportBatch).options(selectinload(ImportBatch.operations)).filter(ImportBatch.id == batch.id).one()
    return serialize_batch(saved_batch)


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
