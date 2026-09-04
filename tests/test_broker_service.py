import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.investing.models.broker import Broker
from app.investing.services.broker_service import BrokerService
from app.investing.services.broker_catalog import (
    BROKER_CATALOG,
    broker_match,
    effective_commission_rate,
    effective_commission_source,
    effective_vat_rate,
    effective_vat_source,
    normalize_broker_name,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Broker.__table__])
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_create_broker_persists_and_lists_it(db):
    created = BrokerService(db).create(
        name="North Star Brokerage",
        country="Saudi Arabia",
        website="https://example.com",
        commission_rate=Decimal("0.155"),
        commission_tax_rate=Decimal("15"),
    )

    assert created.id is not None
    assert created.code.startswith("BRK-")
    assert [item.name for item in BrokerService(db).list()] == [
        "North Star Brokerage"
    ]


def test_create_broker_rejects_duplicate_name(db):
    service = BrokerService(db)
    service.create(name="North Star Brokerage", commission_rate=Decimal("0.155"), commission_tax_rate=Decimal("15"))

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        service.create(name="north star brokerage", commission_rate=Decimal("0.155"), commission_tax_rate=Decimal("15"))


def test_broker_lookup_is_scoped_to_current_user(db):
    broker = BrokerService(db, user_id=1).create(name="North Star Brokerage", commission_rate=Decimal("0.155"), commission_tax_rate=Decimal("15"))

    with pytest.raises(ValueError, match="not found"):
        BrokerService(db, user_id=2).get(broker.id)


def test_similar_catalog_name_must_use_canonical_selection(db):
    with pytest.raises(ValueError, match="Al Rajhi Tadawul"):
        BrokerService(db).create(name="الراجحى")

    broker = BrokerService(db).create(name="Al Rajhi Tadawul", commission_rate=Decimal("0.155"), commission_tax_rate=Decimal("15"))
    assert broker.country == "Saudi Arabia"


def test_unknown_broker_requires_commission_rate(db):
    with pytest.raises(ValueError, match="commission rate"):
        BrokerService(db).create(name="North Star Brokerage")


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("الرياض قلوبال", "Riyad Global"),
        ("دراية قلوبال", "Derayah Global"),
        ("سهم", "Sahm Capital"),
        ("أبيان", "Abyan Trading"),
        ("الأهلي قلوبال", "AlAhli Global"),
    ],
)
def test_local_global_platform_aliases_resolve_to_official_names(query, expected):
    item, _ = broker_match(query)
    assert item is not None
    assert item.name == expected


def test_every_catalog_broker_has_valid_unique_reference_data():
    normalized_names = [normalize_broker_name(item.name) for item in BROKER_CATALOG]
    assert len(normalized_names) == len(set(normalized_names))
    for item in BROKER_CATALOG:
        assert item.name.strip()
        assert item.country.strip()
        assert item.website.startswith("https://")
        assert effective_vat_rate(item) is not None
        assert effective_vat_source(item)
        rate = effective_commission_rate(item)
        if rate is not None:
            assert Decimal("0") <= rate <= Decimal("100")
            assert effective_commission_source(item)


@pytest.mark.parametrize(
    ("query", "expected", "vat"),
    [
        ("IBKR", "Interactive Brokers (IBKR)", Decimal("0")),
        ("Interactive Brokers", "Interactive Brokers (IBKR)", Decimal("0")),
        ("Trade Station", "TradeStation", Decimal("0")),
    ],
)
def test_direct_us_brokers_are_selectable_with_automatic_tax(query, expected, vat):
    item, _ = broker_match(query)
    assert item is not None
    assert item.name == expected
    assert effective_vat_rate(item) == vat
    assert effective_vat_source(item)
    assert effective_commission_source(item)


def test_all_saudi_brokers_receive_automatic_vat():
    saudi_brokers = [item for item in BROKER_CATALOG if item.country == "Saudi Arabia"]
    assert saudi_brokers
    for item in saudi_brokers:
        assert effective_vat_rate(item) == Decimal("15")
        assert effective_vat_source(item) == "Saudi Arabia standard VAT"
