from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.accounting.models import Account, JournalEntry, JournalLine, MonthClose, BankAccount, Loan
from app.accounting.models.loan import PrivateLoanEvent
from app.core.models.user import User
from app.database.base import Base
from app.accounting.services.journal_integrity import AccountingSession
from app.accounting.schemas.private_loan import PrivateLoanRequest, PrivateLoanPaymentRequest, PrivateLoanPriorPaymentRequest, PrivateLoanPriorPaymentBulkRequest
from app.accounting.services.private_loan_service import PrivateLoanService
from app.accounting.services.loan_service import LoanService

@pytest.fixture
def db():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine,tables=[User.__table__,Account.__table__,JournalEntry.__table__,JournalLine.__table__,MonthClose.__table__,BankAccount.__table__,Loan.__table__,PrivateLoanEvent.__table__])
    session=sessionmaker(bind=engine,class_=AccountingSession)()
    session.add_all([User(id=i,email=f'private-loan-{i}@example.test',full_name='Isolated fixture') for i in (1,2)])
    session.add_all([Account(code=code,name=str(code),account_type=kind,normal_balance='DEBIT' if kind in ('ASSET','EXPENSE') else 'CREDIT') for code,kind in [(1120,'ASSET'),(1210,'ASSET'),(2220,'LIABILITY'),(3150,'EQUITY'),(5790,'EXPENSE')]])
    session.add_all([BankAccount(id=i,user_id=i,bank_name='Fixture',account_type='CURRENT',account_name='Isolated',account_identifier=str(i),currency_code='SAR',current_balance=100000) for i in (1,2)])
    session.commit()
    yield session
    session.close();engine.dispose()

def opening(**changes):
    values=dict(name='Synthetic loan',lender='Fixture lender',mode='OPENING',principal=800000,agreed_extra=50000,prior_paid=520000,record_date='2024-07-31',idempotency_key='private-create-fixture-01')
    values.update(changes)
    return PrivateLoanRequest(**values)

def payment(**changes):
    values=dict(amount=80000,payment_date='2025-07-01',bank_account_id=1,idempotency_key='private-payment-fixture-01')
    values.update(changes)
    return PrivateLoanPaymentRequest(**values)

def test_opening_posts_only_remaining_debt_without_cash_or_expense(db):
    loan=PrivateLoanService(db,1).create(opening())
    assert loan.outstanding_balance==Decimal('330000')
    assert loan.monthly_payment==0 and loan.first_payment_date is None
    assert db.get(BankAccount,1).current_balance==100000
    lines=db.query(JournalLine).all()
    assert {db.get(Account,line.account_id).code for line in lines}=={3150,2220}
    assert sum(line.debit for line in lines)==sum(line.credit for line in lines)==330000
    assert loan.private_details['prior_paid']=='520000'

def test_irregular_payment_reduces_bank_and_debt_and_retry_is_safe(db):
    service=PrivateLoanService(db,1);loan=service.create(opening())
    service.pay(loan.id,payment());service.pay(loan.id,payment())
    assert loan.outstanding_balance==250000
    assert db.get(BankAccount,1).current_balance==20000
    assert db.query(JournalEntry).count()==2
    assert len(service.history(loan.id))==2

def test_historical_payment_reduces_debt_without_changing_current_bank_balance(db):
    service=PrivateLoanService(db,1);loan=service.create(opening())
    request=payment(mode='HISTORICAL',bank_account_id=None,historical_source='SNB WORLD credit card',amount=590,idempotency_key='historical-payment-fixture')
    service.pay(loan.id,request)
    assert loan.outstanding_balance==Decimal('329410')
    assert db.get(BankAccount,1).current_balance==100000
    event=service.history(loan.id)[-1]
    assert event['note']=='SNB WORLD credit card'
    entry=db.get(JournalEntry,event['journal_entry_id'])
    assert entry.related_reference==f'private-loan-historical-payment:{loan.id}'

def test_preopening_detail_is_informational_and_capped_at_prior_paid(db):
    service=PrivateLoanService(db,1);loan=service.create(opening())
    request=PrivateLoanPriorPaymentRequest(amount=272000,payment_date='2016-12-31',source='Personal bank loan',idempotency_key='prior-detail-fixture-01')
    service.add_prior_payment_detail(loan.id,request)
    assert loan.outstanding_balance==Decimal('330000')
    assert db.get(BankAccount,1).current_balance==100000
    assert service.history(loan.id)[0]['kind']=='PRIOR_PAYMENT_DETAIL'
    with pytest.raises(ValueError,match='exceed'): service.add_prior_payment_detail(loan.id,PrivateLoanPriorPaymentRequest(amount=300000,payment_date='2017-12-31',source='Other',idempotency_key='prior-detail-fixture-02'))

def test_bulk_preopening_details_save_together(db):
    service=PrivateLoanService(db,1);loan=service.create(opening())
    request=PrivateLoanPriorPaymentBulkRequest(idempotency_key='prior-detail-bulk-fixture',items=[{'amount':45000,'payment_date':'2017-12-31','source':'Savings'},{'amount':25270,'payment_date':'2018-12-31','source':'Salary'}])
    history=service.add_prior_payment_details(loan.id,request)
    assert [item['amount'] for item in history if item['kind']=='PRIOR_PAYMENT_DETAIL']==[Decimal('45000'),Decimal('25270')]
    assert loan.outstanding_balance==Decimal('330000')

def test_creation_retry_and_changed_payload(db):
    service=PrivateLoanService(db,1)
    assert service.create(opening()).id==service.create(opening()).id
    with pytest.raises(ValueError,match='different details'): service.create(opening(agreed_extra=60000))
    assert db.query(Loan).count()==1

@pytest.mark.parametrize('change',[dict(amount=340000),dict(payment_date='2024-07-30'),dict(bank_account_id=2),dict(amount=110000)])
def test_bad_payment_does_not_post(db,change):
    service=PrivateLoanService(db,1);loan=service.create(opening())
    with pytest.raises(ValueError): service.pay(loan.id,payment(**change))
    db.rollback()
    assert db.query(JournalEntry).count()==1
    assert db.get(BankAccount,1).current_balance==100000

def test_user_isolation_and_unsafe_legacy_operations_blocked(db):
    loan=PrivateLoanService(db,1).create(opening())
    with pytest.raises(ValueError): PrivateLoanService(db,2).history(loan.id)
    with pytest.raises(ValueError): LoanService(db,1).void(loan.id)

def test_new_bank_funding_separates_extra_from_received_cash(db):
    loan=PrivateLoanService(db,1).create(opening(mode='BANK',prior_paid=0,bank_account_id=1))
    assert loan.outstanding_balance==850000
    assert db.get(BankAccount,1).current_balance==900000
    assert loan.amount_received==800000

def test_direct_expense_has_no_bank_movement_and_disallows_assets(db):
    service=PrivateLoanService(db,1)
    service.create(opening(mode='DIRECT_EXPENSE',prior_paid=0,expense_account_code=5790,beneficiary='Contractor'))
    assert db.get(BankAccount,1).current_balance==100000
    with pytest.raises(ValueError): service.create(opening(mode='DIRECT_EXPENSE',prior_paid=0,expense_account_code=1210,beneficiary='Seller',idempotency_key='second-fixture-creation'))

def test_invalid_opening_and_nonopening_history_rejected():
    with pytest.raises(ValueError): opening(prior_paid=850000)
    with pytest.raises(ValueError): opening(mode='BANK',bank_account_id=1)
    with pytest.raises(ValueError): opening(bank_account_id=1)

def test_closed_period_rejects_posting(db):
    db.add(MonthClose(user_id=1,period_start=date(2024,7,1),period_end=date(2024,7,31),status='CLOSED',snapshot={},checklist={},checksum='0'*64))
    db.commit()
    with pytest.raises(ValueError,match='closed'): PrivateLoanService(db,1).create(opening())
    db.rollback()
    assert db.query(Loan).count()==db.query(JournalEntry).count()==0
