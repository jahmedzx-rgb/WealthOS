from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.accounting.models import Account, BankAccount, JournalEntry, JournalLine
from app.accounting.models.property_asset import PropertyAsset
from app.accounting.schemas.inheritance import InheritanceRequest
from app.accounting.services.inheritance_service import InheritanceService
from app.database.base import Base


def database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Account.__table__, JournalEntry.__table__, JournalLine.__table__, BankAccount.__table__, PropertyAsset.__table__])
    db = sessionmaker(bind=engine)()
    db.add_all([
        Account(code=1110, name="Cash On Hand", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=1120, name="Bank Accounts", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=1210, name="Real Estate", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=3150, name="Opening Balance Equity", account_type="EQUITY", normal_balance="CREDIT"),
        Account(code=3260, name="Inherited Wealth", account_type="EQUITY", normal_balance="CREDIT"),
    ])
    db.commit()
    return db


def test_received_inheritance_updates_bank_and_uses_inherited_wealth_equity():
    db = database()
    bank = BankAccount(user_id=1, bank_name="Bank", account_type="CURRENT", account_name="Primary", account_identifier="A1", current_balance=Decimal("1000"), currency_code="SAR")
    db.add(bank); db.commit()
    result = InheritanceService(db, 1).execute(InheritanceRequest(timing="RECEIVED_AFTER_START", asset_type="BANK_ACCOUNT", amount=Decimal("5000"), transaction_date=datetime.now(UTC), description="Estate distribution", bank_account_id=bank.id))
    db.refresh(bank)
    lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == result["journal_entry_id"]).all()
    assert bank.current_balance == Decimal("6000")
    assert sum(line.debit for line in lines) == Decimal("5000")
    assert sum(line.credit for line in lines) == Decimal("5000")
    assert db.query(Account).join(JournalLine).filter(JournalLine.journal_entry_id == result["journal_entry_id"], Account.code == 3260).one()


def test_property_inherited_before_wealthos_creates_property_asset():
    db = database()
    result = InheritanceService(db, 1).execute(InheritanceRequest(timing="BEFORE_WEALTHOS", asset_type="PROPERTY", amount=Decimal("700000"), transaction_date=datetime.now(UTC), description="Inherited family home", asset_name="Family Home", property_usage="PRIMARY_RESIDENCE"))
    property_asset = db.query(PropertyAsset).one()
    assert property_asset.name == "Family Home"
    assert property_asset.current_value == Decimal("700000")
    assert result["related_reference"].startswith("opening-inheritance:")
    assert db.query(Account).join(JournalLine).filter(JournalLine.journal_entry_id == result["journal_entry_id"], Account.code == 3150).one()
