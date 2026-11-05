import hashlib
import json
import re
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.models import Account, JournalEntry, JournalLine, PropertyAsset, PropertyOpeningAudit
from app.accounting.schemas.property_asset import OpeningPropertyRequest


class OpeningPropertyConflict(ValueError):
    pass


class OpeningPropertyService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    @staticmethod
    def _canonical_payload(request: OpeningPropertyRequest) -> dict:
        return {
            **request.model_dump(mode="json"),
            "property_name": request.property_name.strip(),
            "market_value_source": (request.market_value_source or "").strip() or None,
            "market_value_note": (request.market_value_note or "").strip() or None,
            "external_property_reference": (request.external_property_reference or "").strip() or None,
        }

    @staticmethod
    def _hash(payload: dict) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def _similarity(request: OpeningPropertyRequest) -> str:
        name = re.sub(r"[^a-z0-9]+", "", request.property_name.casefold())
        acquired = request.acquisition_date.date().isoformat() if request.acquisition_date else "unknown"
        return hashlib.sha256(f"{name}|{acquired}".encode()).hexdigest()

    def execute(self, request: OpeningPropertyRequest) -> dict:
        payload = self._canonical_payload(request)
        payload_hash = self._hash(payload)
        existing = self.db.query(PropertyOpeningAudit).filter(
            PropertyOpeningAudit.user_id == self.user_id,
            PropertyOpeningAudit.idempotency_key == request.idempotency_key,
        ).first()
        if existing:
            if existing.payload_hash != payload_hash:
                raise OpeningPropertyConflict("This idempotency key was already used with different property details.")
            return self._result(existing.property_id, replayed=True)

        external_reference = payload["external_property_reference"]
        if external_reference and self.db.query(PropertyAsset.id).filter(
            PropertyAsset.user_id == self.user_id,
            PropertyAsset.external_reference == external_reference,
        ).first():
            raise OpeningPropertyConflict("This external property reference is already in use.")

        property_account = self.db.query(Account).filter(Account.code == 1210).one_or_none()
        opening_equity = self.db.query(Account).filter(Account.code == 3150).one_or_none()
        adjustment_equity = self.db.query(Account).filter(Account.code == 3250).one_or_none()
        if property_account is None or opening_equity is None or adjustment_equity is None:
            raise ValueError("Opening property ledger accounts are not configured.")

        cost_basis = (request.purchase_price + request.improvement_cost).quantize(Decimal("0.01"))
        current_value = (request.market_value if request.market_value is not None else cost_basis).quantize(Decimal("0.01"))
        similarity = self._similarity(request)
        similar = self.db.query(PropertyOpeningAudit).filter(
            PropertyOpeningAudit.user_id == self.user_id,
            PropertyOpeningAudit.similarity_fingerprint == similarity,
        ).count()

        opening = JournalEntry(
            user_id=self.user_id,
            description=f"Opening property · {payload['property_name']}",
            transaction_date=request.opening_date,
            related_reference=f"opening-property:{request.idempotency_key}",
        )
        self.db.add(opening)
        self.db.flush()
        self.db.add_all([
            JournalLine(journal_entry_id=opening.id, account_id=property_account.id, debit=cost_basis, credit=0),
            JournalLine(journal_entry_id=opening.id, account_id=opening_equity.id, debit=0, credit=cost_basis),
        ])

        valuation = None
        difference = current_value - cost_basis
        if difference:
            valuation = JournalEntry(
                user_id=self.user_id,
                description=f"Opening property valuation · {payload['property_name']} · {payload['market_value_source']}",
                transaction_date=request.opening_date,
                related_reference=f"opening-property-valuation:{request.idempotency_key}",
            )
            self.db.add(valuation)
            self.db.flush()
            amount = abs(difference)
            lines = (
                [JournalLine(journal_entry_id=valuation.id, account_id=property_account.id, debit=amount, credit=0), JournalLine(journal_entry_id=valuation.id, account_id=adjustment_equity.id, debit=0, credit=amount)]
                if difference > 0 else
                [JournalLine(journal_entry_id=valuation.id, account_id=adjustment_equity.id, debit=amount, credit=0), JournalLine(journal_entry_id=valuation.id, account_id=property_account.id, debit=0, credit=amount)]
            )
            self.db.add_all(lines)

        asset = PropertyAsset(
            user_id=self.user_id, acquisition_journal_entry_id=opening.id, valuation_journal_entry_id=valuation.id if valuation else None,
            name=payload["property_name"], usage=request.property_usage,
            income_type=request.property_income_type if request.property_usage == "INVESTMENT_PROPERTY" else None,
            current_value=current_value, acquisition_date=request.acquisition_date.date() if request.acquisition_date else None,
            purchase_price=request.purchase_price, improvement_cost=request.improvement_cost,
            purchase_price_estimated=request.purchase_price_estimated, improvement_cost_estimated=request.improvement_cost_estimated,
            opening_date=request.opening_date.date(), opening_market_value=request.market_value,
            market_value_date=request.market_value_date.date() if request.market_value_date else None,
            market_value_source=payload["market_value_source"], market_value_note=payload["market_value_note"],
            external_reference=external_reference,
        )
        self.db.add(asset)
        self.db.flush()
        self.db.add(PropertyOpeningAudit(
            user_id=self.user_id, property_id=asset.id, idempotency_key=request.idempotency_key,
            payload_hash=payload_hash, similarity_fingerprint=similarity, details=payload,
        ))
        self.db.commit()
        return self._result(asset.id, replayed=False, duplicate_warning=similar > 0)

    def recover_idempotent_replay(self, request: OpeningPropertyRequest) -> dict:
        """Resolve a uniqueness race after the caller rolls back the failed transaction."""
        payload_hash = self._hash(self._canonical_payload(request))
        existing = self.db.query(PropertyOpeningAudit).filter(
            PropertyOpeningAudit.user_id == self.user_id,
            PropertyOpeningAudit.idempotency_key == request.idempotency_key,
        ).one_or_none()
        if existing is None:
            raise OpeningPropertyConflict("The opening property request conflicts with an existing record.")
        if existing.payload_hash != payload_hash:
            raise OpeningPropertyConflict("This idempotency key was already used with different property details.")
        return self._result(existing.property_id, replayed=True)

    def _result(self, property_id: int, *, replayed: bool, duplicate_warning: bool = False) -> dict:
        asset = self.db.query(PropertyAsset).filter(PropertyAsset.id == property_id, PropertyAsset.user_id == self.user_id).one()
        return {
            "id": asset.acquisition_journal_entry_id, "property_asset_id": asset.id,
            "reference": f"property:{asset.acquisition_journal_entry_id}",
            "cost_basis": asset.purchase_price + asset.improvement_cost,
            "current_value": asset.current_value, "opening_journal_entry_id": asset.acquisition_journal_entry_id,
            "valuation_journal_entry_id": asset.valuation_journal_entry_id,
            "replayed": replayed, "duplicate_warning": duplicate_warning,
        }
