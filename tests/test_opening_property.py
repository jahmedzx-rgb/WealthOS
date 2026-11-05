from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.accounting.models import Account, JournalEntry, JournalLine, MonthClose, PropertyAsset, PropertyOpeningAudit
from app.accounting.schemas.property_asset import OpeningPropertyRequest
from app.accounting.services.journal_integrity import AccountingSession
from app.accounting.services.opening_property_service import OpeningPropertyConflict, OpeningPropertyService
from app.accounting.services.period_lock import PeriodClosedError
from app.core.models.user import User
from app.database.base import Base


def database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, JournalEntry.__table__, JournalLine.__table__, PropertyAsset.__table__, PropertyOpeningAudit.__table__])
    db = sessionmaker(bind=engine)()
    db.add_all([
        Account(code=1210, name="Real Estate", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=3150, name="Opening Balance Equity", account_type="EQUITY", normal_balance="CREDIT"),
        Account(code=3250, name="Balance Adjustment Equity", account_type="EQUITY", normal_balance="CREDIT"),
    ])
    db.commit()
    return db


def request(**overrides):
    values = dict(
        property_name="Isolated Test Property", property_usage="PRIMARY_RESIDENCE",
        opening_date=datetime(2024, 7, 31, tzinfo=UTC), acquisition_date=datetime(2020, 2, 1, tzinfo=UTC),
        purchase_price=Decimal("700000.00"), improvement_cost=Decimal("40000.00"),
        market_value=Decimal("900000.00"), market_value_date=datetime(2024, 7, 31, tzinfo=UTC),
        market_value_source="Isolated test appraisal", market_value_note="Synthetic fixture",
        external_property_reference="TEST-PROP-001", idempotency_key="opening-test-property-0001",
    )
    values.update(overrides)
    return OpeningPropertyRequest(**values)


def test_opening_property_posts_cost_and_unrealized_valuation_without_cash_or_income():
    db = database()
    result = OpeningPropertyService(db, 1).execute(request())
    asset = db.query(PropertyAsset).one()
    assert result["cost_basis"] == Decimal("740000.00")
    assert result["current_value"] == Decimal("900000.00")
    assert asset.purchase_price == Decimal("700000.00")
    assert asset.improvement_cost == Decimal("40000.00")
    entries = db.query(JournalEntry).order_by(JournalEntry.id).all()
    assert len(entries) == 2
    opening_lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == entries[0].id).all()
    valuation_lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == entries[1].id).all()
    assert sum(line.debit for line in opening_lines) == sum(line.credit for line in opening_lines) == Decimal("740000.00")
    assert sum(line.debit for line in valuation_lines) == sum(line.credit for line in valuation_lines) == Decimal("160000.00")
    used_codes = {code for (code,) in db.query(Account.code).join(JournalLine).all()}
    assert used_codes == {1210, 3150, 3250}


def test_idempotency_replays_same_payload_and_rejects_changed_payload():
    db = database(); service = OpeningPropertyService(db, 1)
    first = service.execute(request())
    replay = service.execute(request())
    assert replay["replayed"] is True
    assert replay["property_asset_id"] == first["property_asset_id"]
    assert db.query(PropertyAsset).count() == 1
    with pytest.raises(OpeningPropertyConflict):
        service.execute(request(improvement_cost=Decimal("41000.00")))
    assert db.query(PropertyAsset).count() == 1
    assert service.recover_idempotent_replay(request())["replayed"] is True
    with pytest.raises(OpeningPropertyConflict):
        service.recover_idempotent_replay(request(improvement_cost=Decimal("41000.00")))


def test_similar_property_warns_but_distinct_external_reference_is_allowed():
    db = database(); service = OpeningPropertyService(db, 1)
    service.execute(request())
    second = service.execute(request(idempotency_key="opening-test-property-0002", external_property_reference="TEST-PROP-002"))
    assert second["duplicate_warning"] is True
    assert db.query(PropertyAsset).count() == 2


def test_market_value_must_be_on_opening_date():
    with pytest.raises(ValueError, match="dated on the opening date"):
        request(market_value_date=datetime(2024, 8, 1, tzinfo=UTC))


def test_opening_property_is_rejected_inside_closed_period():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, class_=AccountingSession, autoflush=False)()
    db.add(User(id=1, email="opening-property-period@example.test", full_name="Synthetic Period Fixture"))
    db.add_all([
        Account(code=1210, name="Real Estate", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=3150, name="Opening Balance Equity", account_type="EQUITY", normal_balance="CREDIT"),
        Account(code=3250, name="Balance Adjustment Equity", account_type="EQUITY", normal_balance="CREDIT"),
        MonthClose(user_id=1, period_start=date(2024, 7, 1), period_end=date(2024, 7, 31), version=1, status="CLOSED", snapshot={}, checklist={}, checksum="0" * 64),
    ])
    db.commit()
    with pytest.raises(PeriodClosedError):
        OpeningPropertyService(db, 1).execute(request())
    db.rollback()
    assert db.query(PropertyAsset).count() == 0
