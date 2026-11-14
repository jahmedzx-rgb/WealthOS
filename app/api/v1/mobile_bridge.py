from datetime import UTC, datetime, timedelta
from hashlib import sha256
import hmac
import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.account import current_user
from app.api.v1.document_imports import save_batch
from app.core.models.user import User
from app.database.engine import get_db
from app.document_imports.schemas import ImportBatchInput, ImportedOperationInput
from app.mobile_bridge.models import MobileDevice, MobileMessage, MobilePairing
from app.mobile_bridge.parser import parse_financial_message
from app.mobile_bridge.schemas import DeviceSenderUpdate, MobileMessageBatch, PairingClaim, PairingCreate
from app.security.web_auth import check_rate_limit, client_key, token_digest


router = APIRouter(prefix="/mobile", tags=["Mobile bridge"])


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _serialize_device(device: MobileDevice) -> dict:
    return {
        "id": device.id,
        "public_id": device.public_id,
        "device_name": device.device_name,
        "platform": device.platform,
        "status": device.status,
        "sender_allowlist": device.sender_allowlist or [],
        "app_version": device.app_version,
        "os_version": device.os_version,
        "created_at": device.created_at,
        "activated_at": device.activated_at,
        "last_seen_at": device.last_seen_at,
        "last_sync_at": device.last_sync_at,
        "revoked_at": device.revoked_at,
    }


def current_mobile_device(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> MobileDevice:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.casefold() != "bearer" or not token:
        raise HTTPException(status_code=401, detail={"key": "mobile.token_required"})
    device = db.query(MobileDevice).filter(
        MobileDevice.token_hash == token_digest(token),
        MobileDevice.status == "ACTIVE",
    ).first()
    if device is None:
        raise HTTPException(status_code=401, detail={"key": "mobile.token_invalid"})
    return device


@router.post("/pairings")
def create_pairing(
    payload: PairingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    now = datetime.now(UTC)
    db.query(MobilePairing).filter(
        MobilePairing.user_id == user.id,
        MobilePairing.used_at.is_(None),
    ).delete(synchronize_session=False)
    public_id = str(uuid.uuid4())
    secret = secrets.token_urlsafe(32)
    pairing_secret = f"{public_id}.{secret}"
    pairing = MobilePairing(
        public_id=public_id,
        user_id=user.id,
        secret_hash=token_digest(pairing_secret),
        sender_allowlist=payload.sender_allowlist,
        expires_at=now + timedelta(minutes=10),
    )
    db.add(pairing)
    db.commit()
    return {
        "pairing_id": public_id,
        "pairing_secret": pairing_secret,
        "expires_at": pairing.expires_at,
        "sender_allowlist": payload.sender_allowlist,
    }


@router.post("/pairings/claim")
def claim_pairing(payload: PairingClaim, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(db, client_key(request, "mobile-pairing"), 20, 900)
    public_id = payload.pairing_secret.split(".", 1)[0]
    pairing = db.query(MobilePairing).filter(MobilePairing.public_id == public_id).with_for_update().first()
    now = datetime.now(UTC)
    valid = bool(
        pairing
        and pairing.used_at is None
        and _aware(pairing.expires_at) > now
        and hmac.compare_digest(pairing.secret_hash, token_digest(payload.pairing_secret))
    )
    if not valid or pairing is None:
        raise HTTPException(status_code=401, detail={"key": "mobile.pairing_invalid"})
    raw_token = f"wos_{secrets.token_urlsafe(40)}"
    device = db.query(MobileDevice).filter(
        MobileDevice.user_id == pairing.user_id,
        MobileDevice.installation_id == payload.installation_id,
    ).with_for_update().first()
    if device is None:
        device = MobileDevice(
            public_id=str(uuid.uuid4()),
            user_id=pairing.user_id,
            device_name=payload.device_name,
            installation_id=payload.installation_id,
            token_hash=token_digest(raw_token),
            sender_allowlist=pairing.sender_allowlist or [],
        )
        db.add(device)
    else:
        device.device_name = payload.device_name
        device.token_hash = token_digest(raw_token)
        device.status = "ACTIVE"
        device.revoked_at = None
        device.activated_at = now
    device.app_version = payload.app_version
    device.os_version = payload.os_version
    device.sender_allowlist = pairing.sender_allowlist or device.sender_allowlist or []
    pairing.used_at = now
    db.commit()
    db.refresh(device)
    return {
        "device_id": device.public_id,
        "device_token": raw_token,
        "sender_allowlist": device.sender_allowlist or [],
    }


@router.get("/devices")
def list_devices(db: Session = Depends(get_db), user: User = Depends(current_user)):
    devices = db.query(MobileDevice).filter(MobileDevice.user_id == user.id).order_by(MobileDevice.created_at.desc()).all()
    return [_serialize_device(device) for device in devices]


@router.patch("/devices/{device_id}/senders")
def update_device_senders(
    device_id: int,
    payload: DeviceSenderUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    device = db.query(MobileDevice).filter(MobileDevice.id == device_id, MobileDevice.user_id == user.id).first()
    if device is None:
        raise HTTPException(status_code=404, detail={"key": "mobile.device_not_found"})
    device.sender_allowlist = payload.sender_allowlist
    db.commit()
    return _serialize_device(device)


@router.delete("/devices/{device_id}")
def revoke_device(device_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    device = db.query(MobileDevice).filter(MobileDevice.id == device_id, MobileDevice.user_id == user.id).first()
    if device is None:
        raise HTTPException(status_code=404, detail={"key": "mobile.device_not_found"})
    device.status = "REVOKED"
    device.revoked_at = datetime.now(UTC)
    device.token_hash = token_digest(f"revoked_{secrets.token_urlsafe(32)}")
    db.commit()
    return {"id": device.id, "status": device.status}


@router.get("/device/config")
def device_config(device: MobileDevice = Depends(current_mobile_device)):
    return {
        "device_id": device.public_id,
        "sender_allowlist": device.sender_allowlist or [],
        "max_batch_size": 500,
        "review_before_posting": True,
    }


@router.post("/messages/batch")
def ingest_messages(
    payload: MobileMessageBatch,
    db: Session = Depends(get_db),
    device: MobileDevice = Depends(current_mobile_device),
):
    now = datetime.now(UTC)
    device.last_seen_at = now
    accepted_inputs: list[ImportedOperationInput] = []
    accepted_messages = []
    duplicates = ignored = 0
    allowlist = {sender.casefold() for sender in (device.sender_allowlist or [])}
    for message in payload.messages:
        received_at = _aware(message.received_at).astimezone(UTC)
        if received_at > now + timedelta(minutes=10) or received_at < datetime(2010, 1, 1, tzinfo=UTC):
            ignored += 1
            continue
        if allowlist and message.sender.strip().casefold() not in allowlist:
            ignored += 1
            continue
        content_hash = sha256(
            f"{message.sender.strip().casefold()}|{received_at.isoformat()}|{message.body.strip()}".encode("utf-8")
        ).hexdigest()
        exists = db.query(MobileMessage.id).filter(
            ((MobileMessage.device_id == device.id) & (MobileMessage.source_id == message.source_id))
            | ((MobileMessage.user_id == device.user_id) & (MobileMessage.content_hash == content_hash))
        ).first()
        if exists:
            duplicates += 1
            continue
        parsed = parse_financial_message(message.sender, message.body, received_at)
        if parsed is None:
            ignored += 1
            continue
        accepted_inputs.append(ImportedOperationInput(
            operation_type=parsed.operation_type,
            description=parsed.description,
            amount=parsed.amount,
            currency=parsed.currency,
            transaction_date=parsed.transaction_date,
            card_last4=parsed.card_last4,
            confidence=parsed.confidence,
            source_text=parsed.source_text,
        ))
        accepted_messages.append((message, received_at, content_hash))
    batch_id = None
    if accepted_inputs:
        user = db.get(User, device.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail={"key": "mobile.account_unavailable"})
        saved = save_batch(ImportBatchInput(
            filename=f"wealthos-connect-{device.public_id}-{now:%Y%m%dT%H%M%S}.sms.xml",
            file_size=sum(len(message.body.encode("utf-8")) for message, _, _ in accepted_messages),
            file_type="application/vnd.wealthos.sms+json",
            operations=accepted_inputs,
        ), db, user)
        batch_id = saved["id"]
        try:
            for (message, received_at, content_hash), operation in zip(accepted_messages, saved["operations"], strict=True):
                db.add(MobileMessage(
                    user_id=device.user_id,
                    device_id=device.id,
                    source_id=message.source_id,
                    content_hash=content_hash,
                    sender=message.sender.strip(),
                    body=message.body.strip(),
                    received_at=received_at,
                    imported_operation_id=operation["id"],
                ))
            device.last_sync_at = now
            db.commit()
        except IntegrityError:
            db.rollback()
            duplicates += len(accepted_messages)
            accepted_inputs.clear()
    else:
        device.last_sync_at = now
        db.commit()
    return {
        "accepted": len(accepted_inputs),
        "duplicates": duplicates,
        "ignored": ignored,
        "batch_id": batch_id,
        "review_required": bool(accepted_inputs),
    }
