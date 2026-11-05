from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.accounting.models.credit_card_account import CreditCardAccount
from app.accounting.schemas.credit_card_account import CreditCardUpdateRequest

def test_exact_dates_survive_storage_and_edit_schema():
    engine = create_engine('sqlite:///:memory:')
    CreditCardAccount.__table__.create(engine)
    with Session(engine) as db:
        card = CreditCardAccount(user_id=1, issuer_bank='Test', card_name='Test', last4='9999', credit_limit=1000,
                                 payment_due_day=5, payment_due_date=date(2026,9,5), statement_cutoff_date=date(2026,8,10))
        db.add(card)
        db.commit()
        db.refresh(card)
        assert card.payment_due_date == date(2026,9,5)
        assert card.statement_cutoff_date == date(2026,8,10)
    request = CreditCardUpdateRequest(issuer_bank='Test', card_name='Test', last4='9999', credit_limit=1000,
        statement_balance=100, statement_cutoff_day=10, payment_due_day=5, currency_code='SAR',
        payment_due_date='2026-09-05', statement_cutoff_date='2026-08-10')
    assert request.payment_due_date == date(2026,9,5)
    assert request.statement_balance == Decimal('100')
