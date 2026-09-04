from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session

from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.models.month_close import MonthClose


class PeriodClosedError(ValueError):
    """Raised when a write would change an approved accounting period."""


def prevent_changes_to_closed_periods(session: Session, _flush_context, _instances) -> None:
    candidates: dict[tuple[int, object], tuple[int, object]] = {}
    for item in set(session.new).union(session.dirty).union(session.deleted):
        entry = item if isinstance(item, JournalEntry) else item.journal_entry if isinstance(item, JournalLine) else None
        if entry is not None and entry.user_id is not None and entry.transaction_date is not None:
            dates = [entry.transaction_date]
            users = [entry.user_id]
            state = inspect(entry)
            dates.extend(value for value in state.attrs.transaction_date.history.deleted if value is not None)
            users.extend(value for value in state.attrs.user_id.history.deleted if value is not None)
            if entry in session.dirty and state.identity:
                persisted = session.connection().execute(
                    select(JournalEntry.user_id, JournalEntry.transaction_date).where(JournalEntry.id == state.identity[0])
                ).first()
                if persisted:
                    users.append(persisted.user_id)
                    dates.append(persisted.transaction_date)
            for user_id in users:
                for transaction_date in dates:
                    candidates[(user_id, transaction_date)] = (user_id, transaction_date)
    if not candidates or not inspect(session.connection()).has_table("month_closes"):
        return
    with session.no_autoflush:
        for user_id, transaction_date in candidates.values():
            locked = session.query(MonthClose.id).filter(
                MonthClose.user_id == user_id,
                MonthClose.status == "CLOSED",
                MonthClose.period_start <= transaction_date.date(),
                MonthClose.period_end >= transaction_date.date(),
            ).first()
            if locked:
                raise PeriodClosedError("This accounting period is closed. Reopen the month before changing or posting transactions in it.")
