from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import event
from sqlalchemy.orm import Session


TOUCHED_ENTRIES_KEY = "accounting_touched_journal_entries"
TOUCHED_LINES_KEY = "accounting_touched_journal_lines"


def validate_line_amounts(debit: Decimal, credit: Decimal) -> None:
    debit = Decimal(debit or 0)
    credit = Decimal(credit or 0)
    if debit < 0 or credit < 0:
        raise ValueError("Journal debit and credit amounts cannot be negative.")
    if (debit > 0) == (credit > 0):
        raise ValueError("Each journal line must contain exactly one positive debit or credit amount.")


def validate_lines(lines) -> None:
    materialized = list(lines)
    if len(materialized) < 2:
        raise ValueError("A journal entry must contain at least two lines.")
    for line in materialized:
        validate_line_amounts(line.debit, line.credit)
    total_debit = sum((Decimal(line.debit or 0) for line in materialized), Decimal("0"))
    total_credit = sum((Decimal(line.credit or 0) for line in materialized), Decimal("0"))
    if total_debit <= 0:
        raise ValueError("A journal entry must have a positive total.")
    if total_debit != total_credit:
        raise ValueError("Journal entry is not balanced.")


class AccountingSession(Session):
    """Application session that validates every touched journal at commit."""


@event.listens_for(AccountingSession, "before_flush")
def _remember_touched_journals(session, flush_context, instances) -> None:
    from app.accounting.models.journal_entry import JournalEntry
    from app.accounting.models.journal_line import JournalLine
    from app.accounting.services.accounting_period import normalize_accounting_datetime

    entries = session.info.setdefault(TOUCHED_ENTRIES_KEY, set())
    lines = session.info.setdefault(TOUCHED_LINES_KEY, set())
    for item in session.new.union(session.dirty).union(session.deleted):
        if isinstance(item, JournalEntry):
            item.transaction_date = normalize_accounting_datetime(item.transaction_date or datetime.now(UTC))
            entries.add(item)
        elif isinstance(item, JournalLine):
            lines.add(item)


@event.listens_for(AccountingSession, "before_commit")
def _validate_touched_journals(session) -> None:
    from app.accounting.models.journal_entry import JournalEntry
    from app.accounting.models.journal_line import JournalLine

    session.flush()
    entry_ids = {
        item.id
        for item in session.info.get(TOUCHED_ENTRIES_KEY, set())
        if item.id is not None and item not in session.deleted
    }
    entry_ids.update(
        item.journal_entry_id
        for item in session.info.get(TOUCHED_LINES_KEY, set())
        if item.journal_entry_id is not None
    )
    existing_ids = {
        row[0]
        for row in session.query(JournalEntry.id).filter(JournalEntry.id.in_(entry_ids)).all()
    } if entry_ids else set()
    for entry_id in existing_ids:
        lines = session.query(JournalLine).filter(JournalLine.journal_entry_id == entry_id).all()
        validate_lines(lines)


def _clear_tracking(session) -> None:
    session.info.pop(TOUCHED_ENTRIES_KEY, None)
    session.info.pop(TOUCHED_LINES_KEY, None)


@event.listens_for(AccountingSession, "after_commit")
def _clear_after_commit(session) -> None:
    _clear_tracking(session)


@event.listens_for(AccountingSession, "after_rollback")
def _clear_after_rollback(session) -> None:
    _clear_tracking(session)
