"""Read-only, repeatable statement projection from the confirmed baseline and ledger.

Cutoff includes the entire Saudi-local calendar day. Running after downtime catches
up without posting duplicate entries or changing the card's actual debt.
"""
from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import Decimal
from sqlalchemy import or_
from app.accounting.models import Account, JournalEntry, JournalLine

SAUDI = timezone(timedelta(hours=3))
ZERO = Decimal('0.00')

def bounded_statement_amount(value, card, *, include_current_balance):
    amount = max(ZERO, Decimal(value or 0))
    ceiling = max(ZERO, Decimal(card.credit_limit or 0))
    if include_current_balance:
        ceiling = min(ceiling, max(ZERO, Decimal(card.current_balance or 0)))
    return min(amount, ceiling).quantize(Decimal('.01'))

def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value

def month_day(year, month, day):
    return date(year, month, min(day, monthrange(year, month)[1]))

def next_month(value, day):
    return month_day(value.year + (value.month == 12), value.month % 12 + 1, day)

def statement_view(db, card, now=None):
    now = aware(now or datetime.now(UTC))
    start = card.auto_statement_started_at
    if start is None or not card.statement_cutoff_day or not card.payment_due_day:
        statement_balance = bounded_statement_amount(card.statement_balance, card, include_current_balance=True)
        return {'statement_balance': statement_balance, 'payment_due_date': card.payment_due_date,
                'statement_cutoff_date': card.statement_cutoff_date, 'statement_is_estimated': False,
                'issued_statement_balance': statement_balance, 'statement_paid': statement_balance <= 0}
    start = aware(start)
    today = now.astimezone(SAUDI).date()
    cutoff = month_day(today.year, today.month, card.statement_cutoff_day)
    if cutoff >= today:  # today's purchases belong in today's closing statement
        previous = today.replace(day=1) - timedelta(days=1)
        cutoff = month_day(previous.year, previous.month, card.statement_cutoff_day)
    end = datetime.combine(cutoff + timedelta(days=1), time.min, SAUDI)
    closed = end > start
    rows = db.query(JournalEntry, JournalLine).join(JournalLine, JournalLine.journal_entry_id == JournalEntry.id).join(Account, Account.id == JournalLine.account_id).filter(
        JournalEntry.user_id == card.user_id, Account.code == 2110,
        or_(
            JournalEntry.related_reference.in_([f'credit-card-expense:{card.id}', f'credit-card-payment:{card.id}', f'credit-card-adjustment:{card.id}', f'credit-card-cashback:{card.id}']),
            JournalEntry.related_reference.like(f'credit-card-sadad:%:{card.id}'),
            JournalEntry.related_reference.like(f'credit-card-sadad:{card.id}:%'),
        ),
        JournalEntry.created_at >= start, JournalEntry.transaction_date <= now,
    ).all()
    grouped = {}
    for entry, line in rows:
        grouped.setdefault(entry.id, [entry, []])[1].append(line)
    movements = []
    for entry, lines in grouped.values():
        reference = entry.related_reference or ''
        if reference.startswith('credit-card-sadad:'):
            _, source_id, target_id = reference.split(':')
            amount = max((max(Decimal(line.debit or 0), Decimal(line.credit or 0)) for line in lines), default=ZERO)
            effect = amount if int(source_id) == card.id else -amount if int(target_id) == card.id else ZERO
        else:
            effect = sum((Decimal(line.credit or 0) - Decimal(line.debit or 0) for line in lines), ZERO)
        movements.append((entry, effect))
    balance = Decimal(card.auto_statement_opening_balance or 0) if closed else Decimal(card.auto_statement_opening_due or 0)
    for entry, effect in movements:
        if closed and aware(entry.transaction_date) < end:
            balance += effect
    issued_balance = bounded_statement_amount(balance, card, include_current_balance=False)
    for entry, effect in movements:
        if not closed or aware(entry.transaction_date) >= end:
            # Payments and credits after closing reduce the statement; new spending does not.
            if effect < 0:
                balance += effect
    due = card.payment_due_date
    if closed:
        due = month_day(cutoff.year, cutoff.month, card.payment_due_day)
        if due <= cutoff:
            due = next_month(cutoff, card.payment_due_day)
    remaining = bounded_statement_amount(balance, card, include_current_balance=True)
    return {'statement_balance': remaining, 'issued_statement_balance': issued_balance,
            'statement_paid': bool(closed and issued_balance > 0 and remaining == 0),
            'payment_due_date': due, 'statement_cutoff_date': cutoff if closed else card.statement_cutoff_date,
            'statement_is_estimated': closed}

def reset_baseline(card, statement_balance, now=None):
    # A partial payment confirms new balances but must not restart the billing
    # cycle; restarting it makes an unpaid remainder disappear from reminders.
    if card.auto_statement_started_at is None:
        card.auto_statement_started_at = now or datetime.now(UTC)
    card.auto_statement_opening_balance = card.current_balance
    card.auto_statement_opening_due = statement_balance

def validate_card_date(card, value):
    value = aware(value)
    if value > datetime.now(UTC):
        raise ValueError('Future card transactions cannot be posted before they occur.')
    if card.auto_statement_started_at and value.astimezone(SAUDI).date() < aware(card.auto_statement_started_at).astimezone(SAUDI).date():
        raise ValueError('This transaction predates the confirmed card opening balance and would double-count history.')
