from datetime import datetime, time, UTC
from decimal import Decimal
import hashlib
import json

from app.accounting.models.loan import Loan, PrivateLoanEvent
from app.accounting.models.bank_account import BankAccount
from app.core.models.user import User
from app.accounting.schemas.journal import JournalLineInput
from app.accounting.services.account_resolver import AccountResolver
from app.accounting.services.ledger_service import LedgerService


class PrivateLoanService:
    def __init__(self, db, user_id):
        self.db, self.user_id = db, user_id
        self.accounts, self.ledger = AccountResolver(db), LedgerService(db)

    def _lock(self):
        # Serialize this user's private-loan postings, including idempotent retries.
        if not self.db.query(User).filter(User.id == self.user_id).with_for_update().first():
            raise ValueError('User not found.')

    def _fingerprint(self, request, loan_id=None):
        return hashlib.sha256(json.dumps([loan_id, request.model_dump(mode='json')], sort_keys=True).encode()).hexdigest()

    def _replay(self, key, fingerprint):
        event = self.db.query(PrivateLoanEvent).filter_by(user_id=self.user_id, idempotency_key=key).first()
        if event:
            if event.payload_hash != fingerprint:
                raise ValueError('This request key was already used with different details.')
            return self.get(event.loan_id)
        return None

    def get(self, loan_id):
        loan = self.db.query(Loan).filter_by(id=loan_id, user_id=self.user_id, loan_type='PRIVATE_FLEXIBLE').first()
        if not loan:
            raise ValueError('Private loan not found.')
        return loan

    def _bank(self, bank_id):
        bank = self.db.query(BankAccount).filter_by(id=bank_id, user_id=self.user_id).with_for_update().first()
        if bank is None or bank.currency_code != 'SAR':
            raise ValueError('Select your SAR bank account.')
        return bank

    def _line(self, code, debit=0, credit=0):
        return JournalLineInput(account_id=self.accounts.get_by_code(code).id, debit=debit, credit=credit)

    def create(self, request):
        self._lock()
        fingerprint = self._fingerprint(request)
        replay = self._replay(request.idempotency_key, fingerprint)
        if replay:
            return replay
        total = request.principal + request.agreed_extra
        outstanding = total - request.prior_paid
        bank = None
        if request.mode == 'OPENING':
            lines = [self._line(3150, debit=outstanding), self._line(2220, credit=outstanding)]
            destination = 3150
        else:
            if request.mode == 'BANK':
                bank = self._bank(request.bank_account_id)
                destination = 1120
            else:
                expense = self.accounts.get_by_code(request.expense_account_code)
                if expense.account_type != 'EXPENSE' or not expense.is_active:
                    raise ValueError('Direct expense funding requires an active expense account, not an existing asset.')
                destination = expense.code
            lines = [self._line(destination, debit=request.principal), self._line(2220, credit=total)]
            if request.agreed_extra:
                lines.append(self._line(5790, debit=request.agreed_extra))
        entry = self.ledger.post(description=f'Private loan: {request.name}', lines=lines, user_id=self.user_id,
            transaction_date=datetime.combine(request.record_date, time(12), tzinfo=UTC),
            related_reference=f'private-loan:{request.idempotency_key}' + (f':bank-account:{bank.id}' if bank else ''))
        details = request.model_dump(mode='json', exclude={'idempotency_key'})
        loan = Loan(user_id=self.user_id, name=request.name.strip(), lender=request.lender.strip(),
            loan_type='PRIVATE_FLEXIBLE', principal_amount=request.principal, outstanding_balance=outstanding,
            amount_received=request.principal if bank else Decimal('0'), fees=Decimal('0'), annual_rate=Decimal('0'),
            term_months=0, monthly_payment=Decimal('0'), first_payment_date=None,
            destination_account_code=destination, destination_bank_account_id=bank.id if bank else None,
            liability_account_code=2220, journal_entry_id=entry.id, private_details=details, status='ACTIVE')
        self.db.add(loan)
        self.db.flush()
        self.db.add(PrivateLoanEvent(user_id=self.user_id, loan_id=loan.id, kind=request.mode,
            event_date=request.record_date, amount=outstanding, journal_entry_id=entry.id,
            idempotency_key=request.idempotency_key, payload_hash=fingerprint, note=request.note))
        if bank:
            bank.current_balance += request.principal
        self.db.commit()
        self.db.refresh(loan)
        return loan

    def pay(self, loan_id, request):
        self._lock()
        fingerprint = self._fingerprint(request, loan_id)
        replay = self._replay(request.idempotency_key, fingerprint)
        if replay:
            return replay
        loan = self.get(loan_id)
        if loan.status != 'ACTIVE' or request.amount > loan.outstanding_balance:
            raise ValueError('Payment exceeds the active loan balance.')
        if request.payment_date.isoformat() < loan.private_details['record_date']:
            raise ValueError('Payment must not precede the opening or funding date.')
        bank = None
        if request.mode == 'BANK':
            bank = self._bank(request.bank_account_id)
            if bank.current_balance < request.amount:
                raise ValueError('The payment bank account has insufficient funds.')
            reference = f'private-loan-payment:{loan.id}:bank-account:{bank.id}'
            lines = [self._line(2220, debit=request.amount), self._line(1120, credit=request.amount)]
        else:
            reference = f'private-loan-historical-payment:{loan.id}'
            lines = [self._line(2220, debit=request.amount), self._line(3150, credit=request.amount)]
        entry = self.ledger.post(description=f'Private loan payment: {loan.name}', user_id=self.user_id,
            transaction_date=datetime.combine(request.payment_date, time(12), tzinfo=UTC), related_reference=reference, lines=lines)
        loan.outstanding_balance -= request.amount
        if bank:
            bank.current_balance -= request.amount
        if loan.outstanding_balance == 0:
            loan.status = 'SETTLED'
        self.db.add(PrivateLoanEvent(user_id=self.user_id, loan_id=loan.id, kind='PAYMENT',
            event_date=request.payment_date, amount=request.amount, journal_entry_id=entry.id,
            idempotency_key=request.idempotency_key, payload_hash=fingerprint,
            note=(f'{request.historical_source.strip()} · {request.note.strip()}'.strip(' ·') if request.mode == 'HISTORICAL' else request.note)))
        self.db.commit()
        self.db.refresh(loan)
        return loan

    def history(self, loan_id):
        self.get(loan_id)
        events = self.db.query(PrivateLoanEvent).filter_by(loan_id=loan_id, user_id=self.user_id).order_by(PrivateLoanEvent.event_date, PrivateLoanEvent.id).all()
        return [{key: getattr(item, key) for key in ('id', 'kind', 'event_date', 'amount', 'journal_entry_id', 'note')} for item in events]

    def update(self, loan_id, request):
        loan = self.get(loan_id)
        loan.name = request.name.strip()
        loan.lender = request.lender.strip()
        details = dict(loan.private_details or {})
        details['note'] = request.note.strip()
        loan.private_details = details
        self.db.commit()
        self.db.refresh(loan)
        return loan

    def add_prior_payment_detail(self, loan_id, request):
        self._lock()
        fingerprint = self._fingerprint(request, loan_id)
        replay = self._replay(request.idempotency_key, fingerprint)
        if replay:
            return self.history(loan_id)
        loan = self.get(loan_id)
        record_date = loan.private_details.get('record_date') if loan.private_details else None
        if not record_date or request.payment_date.isoformat() >= record_date:
            raise ValueError('A pre-opening payment must be dated before the opening balance date.')
        prior_paid = Decimal(str(loan.private_details.get('prior_paid', '0')))
        recorded = sum((item.amount for item in self.db.query(PrivateLoanEvent).filter_by(loan_id=loan.id, user_id=self.user_id, kind='PRIOR_PAYMENT_DETAIL').all()), Decimal('0'))
        if recorded + request.amount > prior_paid:
            raise ValueError('Pre-opening payment details exceed the recorded paid-before-opening total.')
        detail_note = f'{request.source.strip()} · {request.note.strip()}'.strip(' ·')
        self.db.add(PrivateLoanEvent(user_id=self.user_id, loan_id=loan.id, kind='PRIOR_PAYMENT_DETAIL',
            event_date=request.payment_date, amount=request.amount, journal_entry_id=None,
            idempotency_key=request.idempotency_key, payload_hash=fingerprint, note=detail_note))
        self.db.commit()
        return self.history(loan_id)

    def add_prior_payment_details(self, loan_id, request):
        self._lock()
        fingerprint = self._fingerprint(request, loan_id)
        existing = self.db.query(PrivateLoanEvent).filter_by(user_id=self.user_id, idempotency_key=f'{request.idempotency_key}:0').first()
        if existing:
            if existing.payload_hash != fingerprint:
                raise ValueError('This request key was already used with different details.')
            return self.history(loan_id)
        loan = self.get(loan_id)
        record_date = loan.private_details.get('record_date') if loan.private_details else None
        if not record_date or any(item.payment_date.isoformat() >= record_date for item in request.items):
            raise ValueError('Every pre-opening payment must be dated before the opening balance date.')
        prior_paid = Decimal(str(loan.private_details.get('prior_paid', '0')))
        recorded = sum((item.amount for item in self.db.query(PrivateLoanEvent).filter_by(loan_id=loan.id, user_id=self.user_id, kind='PRIOR_PAYMENT_DETAIL').all()), Decimal('0'))
        if recorded + sum((item.amount for item in request.items), Decimal('0')) > prior_paid:
            raise ValueError('Pre-opening payment details exceed the recorded paid-before-opening total.')
        for index, item in enumerate(request.items):
            detail_note = f'{item.source.strip()} · {item.note.strip()}'.strip(' ·')
            self.db.add(PrivateLoanEvent(user_id=self.user_id, loan_id=loan.id, kind='PRIOR_PAYMENT_DETAIL', event_date=item.payment_date,
                amount=item.amount, journal_entry_id=None, idempotency_key=f'{request.idempotency_key}:{index}', payload_hash=fingerprint, note=detail_note))
        self.db.commit()
        return self.history(loan_id)
