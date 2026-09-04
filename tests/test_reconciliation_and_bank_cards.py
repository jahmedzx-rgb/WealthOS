from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database.model_registry  # noqa: F401
from app.accounting.models.account import Account
from app.accounting.models.bank_account import BankAccount
from app.accounting.models.bank_card import BankCard
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.schemas.bank_card import BankCardRequest
from app.api.v1.accounting import create_bank_card, reconciliation
from app.core.models.user import User
from app.database.base import Base
from app.document_imports.models import ImportBatch, ImportedOperation


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id=1, email="reconcile@example.com", full_name="Reconcile Test")
    db.add(user)
    db.commit()
    return db, user


def test_bank_card_inherits_owned_bank_account_currency():
    db, user = make_db()
    bank = BankAccount(user_id=user.id, bank_name="Bank", account_type="CURRENT", account_name="Primary", account_identifier="SA1000", current_balance=0, currency_code="SAR")
    db.add(bank); db.commit()
    result = create_bank_card(BankCardRequest(bank_account_id=bank.id, card_name="Mada", last4="1234", card_network="MADA"), db, user)
    assert result["currency_code"] == "SAR"
    assert db.query(BankCard).filter(BankCard.user_id == user.id).count() == 1


def test_reconciliation_suggests_exact_amount_and_date_match():
    db, user = make_db()
    account = Account(code=1120, name="Bank", account_type="ASSET", normal_balance="DEBIT")
    db.add(account); db.flush()
    entry = JournalEntry(user_id=user.id, description="Imported transfer", transaction_date=datetime(2026, 8, 30, tzinfo=UTC))
    db.add(entry); db.flush()
    db.add(JournalLine(journal_entry_id=entry.id, account_id=account.id, debit=Decimal("250.00"), credit=0))
    batch = ImportBatch(user_id=user.id, filename="statement.xls", file_size=10, status="PENDING_REVIEW")
    batch.operations = [ImportedOperation(operation_type="Transfer", description="Bank transfer", amount=Decimal("250.00"), currency="SAR", transaction_date="30/08/2026", confidence=90, source_text="transfer", status="PENDING")]
    db.add(batch); db.commit()
    result = reconciliation(db, user)
    assert result["suggested"] == 1
    assert result["items"][0]["journal_entry_id"] == entry.id
