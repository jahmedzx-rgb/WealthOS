from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import app.database.model_registry
from app.database.base import Base
from app.core.models.user import User
from app.accounting.models import Account, CreditCardAccount, JournalEntry, JournalLine
from app.accounting.schemas.expense import ExpenseRequest
from app.accounting.services.expense_service import ExpenseService
from app.accounting.services.card_statement_service import reset_baseline, statement_view, validate_card_date

@pytest.fixture
def setup():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id=1, email='card@test.local', full_name='Test'))
        liability = Account(code=2110, name='Cards', account_type='LIABILITY', normal_balance='CREDIT')
        expense = Account(code=5100, name='Expense', account_type='EXPENSE', normal_balance='DEBIT')
        db.add_all([liability, expense])
        card = CreditCardAccount(user_id=1, issuer_bank='Test', card_name='Card', last4='0001', credit_limit=5000,
            current_balance=1000, statement_balance=0, statement_cutoff_day=10, payment_due_day=5,
            auto_statement_started_at=datetime(2026,9,6,tzinfo=UTC), auto_statement_opening_balance=1000, auto_statement_opening_due=0)
        db.add(card); db.commit()
        yield db, card, liability, expense

def movement(db, card, liability, expense, day, credit=0, debit=0, user_id=1, reference=None):
    entry=JournalEntry(user_id=user_id,description='Test',transaction_date=datetime(2026,9,day,12,tzinfo=UTC),
        created_at=datetime(2026,9,day,13,tzinfo=UTC),related_reference=reference or (f'credit-card-expense:{card.id}' if credit else f'credit-card-payment:{card.id}'))
    db.add(entry);db.flush()
    db.add_all([JournalLine(journal_entry_id=entry.id,account_id=liability.id,credit=credit,debit=debit),
        JournalLine(journal_entry_id=entry.id,account_id=expense.id,credit=debit,debit=credit)])
    db.commit()

def test_cycle_excludes_later_spending_counts_payments_once_and_catches_up(setup):
    db,card,liability,expense=setup
    movement(db,card,liability,expense,8,credit=200)
    movement(db,card,liability,expense,9,debit=100)
    movement(db,card,liability,expense,12,credit=300)
    movement(db,card,liability,expense,13,debit=400)
    before=statement_view(db,card,datetime(2026,9,10,12,tzinfo=UTC))
    assert before['statement_balance']==0
    view=statement_view(db,card,datetime(2026,9,14,tzinfo=UTC))
    assert view['statement_balance']==700
    assert view['issued_statement_balance']==1100
    assert view['statement_paid'] is False
    assert view['payment_due_date']==date(2026,10,5)
    assert view['statement_is_estimated'] is True
    assert statement_view(db,card,datetime(2026,9,14,tzinfo=UTC))==view
    assert statement_view(db,card,datetime(2026,10,11,tzinfo=UTC))['statement_balance']==1000
    assert card.current_balance==1000  # reading never posts or changes actual debt

def test_statement_projection_never_exceeds_card_debt_or_limit(setup):
    db,card,liability,expense=setup
    card.current_balance=Decimal('5000')
    card.auto_statement_opening_balance=Decimal('5000')
    movement(db,card,liability,expense,8,credit=5000)
    view=statement_view(db,card,datetime(2026,9,14,tzinfo=UTC))
    assert view['issued_statement_balance']==Decimal('5000.00')
    assert view['statement_balance']==Decimal('5000.00')

def test_legacy_statement_balance_is_bounded_for_every_card(setup):
    db,card,_,_=setup
    card.auto_statement_started_at=None
    card.credit_limit=Decimal('5000')
    card.current_balance=Decimal('3000')
    card.statement_balance=Decimal('9000')
    view=statement_view(db,card,datetime(2026,9,14,tzinfo=UTC))
    assert view['issued_statement_balance']==Decimal('3000.00')
    assert view['statement_balance']==Decimal('3000.00')

def test_end_of_day_year_rollover_and_short_month(setup):
    db,card,_,_=setup
    card.statement_cutoff_day=31
    assert statement_view(db,card,datetime(2026,12,31,20,59,tzinfo=UTC))['statement_cutoff_date']==date(2026,11,30)
    assert statement_view(db,card,datetime(2026,12,31,21,tzinfo=UTC))['payment_due_date']==date(2027,1,5)
    assert statement_view(db,card,datetime(2027,3,1,tzinfo=UTC))['statement_cutoff_date']==date(2027,2,28)

def test_card_expense_posts_liability_not_bank_and_validates_source(setup):
    db,card,_,_=setup
    now=datetime.now(UTC)
    card.auto_statement_started_at=now-timedelta(hours=1);db.commit()
    request=ExpenseRequest(expense_account_code=5100,payment_credit_card_id=card.id,amount=100,transaction_date=now,description='Purchase')
    entry=ExpenseService(db,1).execute(request)
    assert card.current_balance==1100
    assert entry.related_reference==f'credit-card-expense:{card.id}'
    lines=db.query(JournalLine).filter_by(journal_entry_id=entry.id).all()
    assert sum(line.debit for line in lines)==sum(line.credit for line in lines)==100
    with pytest.raises(ValueError): ExpenseService(db,2).execute(request)
    with pytest.raises(ValueError): ExpenseService(db,1).execute(request.model_copy(update={'amount':Decimal(10000)}))
    with pytest.raises(ValueError): validate_card_date(card,now-timedelta(days=1))
    with pytest.raises(ValueError): validate_card_date(card,now+timedelta(days=1))

def test_payments_never_make_negative_due(setup):
    db,card,liability,expense=setup
    movement(db,card,liability,expense,12,debit=1500)
    view=statement_view(db,card,datetime(2026,9,14,tzinfo=UTC))
    assert view['statement_balance']==0
    assert view['issued_statement_balance']==1000
    assert view['statement_paid'] is True

def test_partial_payment_baseline_keeps_existing_billing_cycle(setup):
    _,card,_,_=setup
    original_start=card.auto_statement_started_at
    card.current_balance=Decimal('750')
    reset_baseline(card,Decimal('750'),datetime(2026,9,22,tzinfo=UTC))
    assert card.auto_statement_started_at==original_start
    assert card.auto_statement_opening_balance==Decimal('750')
    assert card.auto_statement_opening_due==Decimal('750')

def test_card_to_card_sadad_reduces_target_statement_but_not_source_statement(setup):
    db,card,liability,expense=setup
    card.auto_statement_opening_due=Decimal('1000')
    movement(db,card,liability,expense,12,debit=400,reference=f'credit-card-sadad:99:{card.id}')
    movement(db,card,liability,expense,13,credit=250,reference=f'credit-card-sadad:{card.id}:88')
    view=statement_view(db,card,datetime(2026,9,14,tzinfo=UTC))
    assert view['issued_statement_balance']==Decimal('1000.00')
    assert view['statement_balance']==Decimal('600.00')
