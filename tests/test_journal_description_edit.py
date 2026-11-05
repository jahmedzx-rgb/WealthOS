from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.accounting.models.journal_entry import JournalEntry, JournalEntryDescriptionAudit
from app.api.v1.accounting import JournalEntryDescriptionUpdate, update_journal_entry_description
from app.core.models.user import User
from app.database.base import Base


def test_description_edit_changes_only_text_and_keeps_an_audit_record():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[User.__table__, JournalEntry.__table__, JournalEntryDescriptionAudit.__table__])
    db = sessionmaker(bind=engine)()
    user = User(id=1, email="description@example.com", full_name="Description Test")
    entry = JournalEntry(user_id=1, description="PS5 renewal", transaction_date=datetime(2026, 9, 15, 8, 35, tzinfo=UTC), related_reference="credit-card-expense:5")
    db.add_all([user, entry]); db.commit(); db.refresh(entry)

    original_date = entry.transaction_date
    original_reference = entry.related_reference
    result = update_journal_entry_description(entry.id, JournalEntryDescriptionUpdate(description="PlayStation Plus renewal"), db, user)

    db.refresh(entry)
    audit = db.query(JournalEntryDescriptionAudit).one()
    assert result["description"] == "PlayStation Plus renewal"
    assert entry.description == "PlayStation Plus renewal"
    assert entry.transaction_date == original_date
    assert entry.related_reference == original_reference
    assert audit.previous_description == "PS5 renewal"
    assert audit.new_description == "PlayStation Plus renewal"
