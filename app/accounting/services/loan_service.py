from __future__ import annotations

from datetime import UTC, datetime, time
from decimal import Decimal
import hashlib
import json
from math import ceil, log

from sqlalchemy.orm import Session

from app.accounting.models.loan import Loan, LoanPayment
from app.accounting.models.bank_account import BankAccount
from app.accounting.schemas.journal import JournalLineInput
from app.accounting.schemas.loan import LoanRequest, LoanRefinanceRequest, LoanSettlementRequest, LoanUpdateRequest, LoanPaymentRequest
from app.accounting.services.account_resolver import AccountResolver
from app.accounting.services.ledger_service import LedgerService
from app.core.models.user import User


class LoanService:
    LIABILITY_CODES = {"SHORT_TERM": 2140, "LONG_TERM": 2220, "MORTGAGE": 2210}

    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.accounts = AccountResolver(db)
        self.ledger = LedgerService(db)
        self.user_id = user_id

    def create(self, request: LoanRequest) -> Loan:
        liability_code = self.LIABILITY_CODES[request.loan_type]
        liability = self.accounts.get_by_code(liability_code)
        bank_record = None
        if request.destination_bank_account_id:
            bank_record = self.db.query(BankAccount).filter(BankAccount.id == request.destination_bank_account_id, BankAccount.user_id == self.user_id).first()
            if bank_record is None:
                raise ValueError("Select a valid destination bank account.")
        payment_bank_record = self.db.query(BankAccount).filter(BankAccount.id == request.payment_bank_account_id, BankAccount.user_id == self.user_id).first() if request.payment_bank_account_id else None
        if request.payment_bank_account_id and payment_bank_record is None:
            raise ValueError("Select a valid payment bank account.")
        if request.recording_method == "OPENING":
            opening_equity = self.accounts.get_by_code(3150)
            outstanding = request.current_outstanding_balance or (request.monthly_payment * request.remaining_installments + request.bank_balance_adjustment)
            lines = [
                JournalLineInput(account_id=opening_equity.id, debit=outstanding, credit=Decimal("0.00")),
                JournalLineInput(account_id=liability.id, debit=Decimal("0.00"), credit=outstanding),
            ]
            entry = self.ledger.post(
                description=f"Opening loan balance: {request.name}", lines=lines, user_id=self.user_id,
                transaction_date=datetime.combine(request.opening_balance_date, time(12), tzinfo=UTC),
                related_reference=f"loan-opening:{request.name}",
            )
            private_details = {
                "recording_method": "OPENING",
                "opening_balance_date": request.opening_balance_date.isoformat(),
                "remaining_installments": request.remaining_installments,
                "current_outstanding_balance": str(outstanding),
                "early_settlement_amount": str(request.early_settlement_amount) if request.early_settlement_amount is not None else None,
                "bank_balance_adjustment": str(request.bank_balance_adjustment),
                "payment_day": request.payment_day,
                "historical_receiving_bank_account_id": request.destination_bank_account_id,
                "payment_bank_account_id": request.payment_bank_account_id,
            }
        else:
            bank = self.accounts.get_by_code(request.destination_account_code)
            outstanding = request.principal_amount
            lines = [
                JournalLineInput(account_id=bank.id, debit=request.amount_received, credit=Decimal("0.00")),
                JournalLineInput(account_id=liability.id, debit=Decimal("0.00"), credit=request.principal_amount),
            ]
            if request.fees:
                fees = self.accounts.get_by_code(5790)
                lines.insert(1, JournalLineInput(account_id=fees.id, debit=request.fees, credit=Decimal("0.00")))
            entry = self.ledger.post(description=f"New loan: {request.name}", lines=lines, user_id=self.user_id, related_reference=f"loan-funding:bank-account:{bank_record.id}")
            private_details = {"recording_method": "BANK", "payment_day": request.payment_day, "payment_bank_account_id": request.payment_bank_account_id, "remaining_installments": request.term_months}
        loan = Loan(
            user_id=self.user_id, name=request.name, lender=request.lender, loan_type=request.loan_type,
            principal_amount=request.principal_amount, outstanding_balance=outstanding,
            amount_received=request.amount_received, fees=request.fees, annual_rate=request.annual_rate,
            term_months=request.term_months, monthly_payment=request.monthly_payment,
            first_payment_date=request.first_payment_date, destination_account_code=request.destination_account_code,
            destination_bank_account_id=request.destination_bank_account_id, liability_account_code=liability_code,
            journal_entry_id=entry.id, private_details=private_details,
        )
        self.db.add(loan)
        if request.recording_method == "BANK":
            bank_record.current_balance += request.amount_received
        self.db.commit()
        self.db.refresh(loan)
        return loan

    def list(self) -> list[Loan]:
        return self.db.query(Loan).filter(Loan.user_id == self.user_id).order_by(Loan.created_at.desc()).all()

    def get(self, loan_id: int) -> Loan:
        loan = self.db.query(Loan).filter(Loan.id == loan_id, Loan.user_id == self.user_id).first()
        if loan is None:
            raise ValueError("Loan not found.")
        return loan

    def update(self, loan_id: int, request: LoanUpdateRequest) -> Loan:
        loan = self.get(loan_id)
        if loan.loan_type == 'PRIVATE_FLEXIBLE':
            raise ValueError('Use the private loan workflow; scheduled-loan edits are not supported.')
        if loan.status != "ACTIVE":
            raise ValueError("Only active loans can be edited.")
        values = request.model_dump()
        payment_day = values.pop("payment_day", None) or request.first_payment_date.day
        payment_bank_account_id = values.pop("payment_bank_account_id", None) or loan.destination_bank_account_id
        if payment_bank_account_id is not None:
            bank_record = self.db.query(BankAccount).filter(BankAccount.id == payment_bank_account_id, BankAccount.user_id == self.user_id).first()
            if bank_record is None:
                raise ValueError("Select a valid payment bank account.")
        for field, value in values.items():
            setattr(loan, field, value)
        details = dict(loan.private_details or {})
        details["payment_day"] = payment_day
        details["payment_bank_account_id"] = payment_bank_account_id
        details["remaining_installments"] = self._remaining_installments(loan)
        loan.private_details = details
        self.db.commit(); self.db.refresh(loan)
        return loan

    def void(self, loan_id: int) -> Loan:
        loan = self.get(loan_id)
        if loan.loan_type == 'PRIVATE_FLEXIBLE':
            raise ValueError('Private loan cancellation requires an audited correction and is not available yet.')
        if loan.status != "ACTIVE":
            raise ValueError("Only active loans can be voided.")
        from app.accounting.models.journal_line import JournalLine
        original_lines = self.db.query(JournalLine).filter(JournalLine.journal_entry_id == loan.journal_entry_id).all()
        reversal = [JournalLineInput(account_id=line.account_id, debit=line.credit, credit=line.debit) for line in original_lines]
        self.ledger.post(description=f"Void loan: {loan.name}", lines=reversal, user_id=self.user_id)
        if loan.destination_bank_account_id is not None:
            bank_record = self.db.query(BankAccount).filter(BankAccount.id == loan.destination_bank_account_id, BankAccount.user_id == self.user_id).first()
            if bank_record is not None:
                bank_record.current_balance -= loan.amount_received
        loan.status = "VOID"; loan.outstanding_balance = Decimal("0.00")
        self.db.commit(); self.db.refresh(loan)
        return loan

    def settle(self, loan_id: int, request: LoanSettlementRequest) -> Loan:
        loan = self.get(loan_id)
        if loan.loan_type == 'PRIVATE_FLEXIBLE':
            raise ValueError('Use the private loan payment workflow.')
        if loan.status != "ACTIVE":
            raise ValueError("Only active loans can be settled.")
        liability = self.accounts.get_by_code(loan.liability_account_code)
        bank = self.accounts.get_by_code(request.payment_account_code)
        bank_record = self.db.query(BankAccount).filter(BankAccount.id == request.payment_bank_account_id, BankAccount.user_id == self.user_id).first()
        if bank_record is None:
            raise ValueError("Select a valid settlement bank account.")
        if bank_record.current_balance < request.settlement_amount:
            raise ValueError("The settlement bank account does not have sufficient funds.")
        outstanding = loan.outstanding_balance
        lines = [JournalLineInput(account_id=liability.id, debit=outstanding, credit=Decimal("0.00")), JournalLineInput(account_id=bank.id, debit=Decimal("0.00"), credit=request.settlement_amount)]
        difference = request.settlement_amount - outstanding
        if difference > 0:
            expense = self.accounts.get_by_code(5790); lines.append(JournalLineInput(account_id=expense.id, debit=difference, credit=Decimal("0.00")))
        elif difference < 0:
            income = self.accounts.get_by_code(4900); lines.append(JournalLineInput(account_id=income.id, debit=Decimal("0.00"), credit=-difference))
        self.ledger.post(description=f"Early settlement: {loan.name}", lines=lines, user_id=self.user_id, related_reference=f"loan-settlement:{loan.id}:bank-account:{bank_record.id}")
        bank_record.current_balance -= request.settlement_amount
        loan.status = "SETTLED"; loan.outstanding_balance = Decimal("0.00")
        self.db.commit(); self.db.refresh(loan)
        return loan

    def record_payment(self, loan_id: int, request: LoanPaymentRequest) -> LoanPayment:
        if not self.db.query(User).filter(User.id == self.user_id).with_for_update().first():
            raise ValueError("User not found.")
        fingerprint = hashlib.sha256(json.dumps(request.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
        replay = self.db.query(LoanPayment).filter_by(user_id=self.user_id, idempotency_key=request.idempotency_key).first()
        if replay:
            if replay.payload_hash != fingerprint or replay.loan_id != loan_id:
                raise ValueError("This payment request key was already used with different details.")
            return replay

        loan = self.get(loan_id)
        if loan.loan_type == "PRIVATE_FLEXIBLE":
            raise ValueError("Use the private-loan payment workflow.")
        if loan.status != "ACTIVE":
            raise ValueError("Only active loans can receive installment payments.")
        if loan.first_payment_date and request.payment_date < loan.first_payment_date:
            raise ValueError("Payment date cannot precede the first installment date.")
        bank_record = self.db.query(BankAccount).filter(
            BankAccount.id == request.payment_bank_account_id, BankAccount.user_id == self.user_id
        ).with_for_update().first()
        if bank_record is None or bank_record.currency_code != "SAR":
            raise ValueError("Select a valid SAR bank account.")
        if bank_record.current_balance < request.amount:
            raise ValueError("The selected bank account does not have sufficient funds.")

        details = dict(loan.private_details or {})
        recorded = self.db.query(LoanPayment).filter_by(user_id=self.user_id, loan_id=loan.id).order_by(LoanPayment.installment_number.desc()).first()
        remaining = int(details.get("remaining_installments") or self._remaining_installments(loan))
        installment_number = loan.term_months - remaining + 1
        if recorded:
            installment_number = max(installment_number, recorded.installment_number + 1)
            if request.payment_date <= recorded.payment_date:
                raise ValueError("Each installment must be recorded after the previous payment date.")
        if remaining <= 0:
            raise ValueError("This loan has no scheduled installments remaining.")

        interest_paid = (loan.outstanding_balance * loan.annual_rate / Decimal("1200")).quantize(Decimal("0.01"))
        principal_paid = request.amount - interest_paid
        if principal_paid <= 0:
            raise ValueError("This installment does not cover the estimated monthly interest.")
        if principal_paid > loan.outstanding_balance:
            raise ValueError("This amount exceeds the scheduled installment balance. Use Early settlement for a full payoff.")
        outstanding_after = loan.outstanding_balance - principal_paid
        if outstanding_after < Decimal("0.01"):
            principal_paid = loan.outstanding_balance
            interest_paid = request.amount - principal_paid
            outstanding_after = Decimal("0.00")
        loan.outstanding_balance = outstanding_after
        next_remaining = 0 if outstanding_after == 0 else self._remaining_installments(loan)

        liability = self.accounts.get_by_code(loan.liability_account_code)
        bank = self.accounts.get_by_code(1120)
        lines = [
            JournalLineInput(account_id=liability.id, debit=principal_paid, credit=Decimal("0.00")),
            JournalLineInput(account_id=bank.id, debit=Decimal("0.00"), credit=request.amount),
        ]
        if interest_paid:
            finance_cost = self.accounts.get_by_code(5790)
            lines.append(JournalLineInput(account_id=finance_cost.id, debit=interest_paid, credit=Decimal("0.00")))
        entry = self.ledger.post(
            description=f"Loan installment {installment_number}: {loan.name}", lines=lines, user_id=self.user_id,
            transaction_date=datetime.combine(request.payment_date, time(12), tzinfo=UTC),
            related_reference=f"loan-payment:{loan.id}:installment:{installment_number}:bank-account:{bank_record.id}",
        )
        details["remaining_installments"] = next_remaining
        details["current_outstanding_balance"] = str(outstanding_after)
        loan.private_details = details
        if outstanding_after == 0:
            loan.status = "SETTLED"
        bank_record.current_balance -= request.amount
        payment = LoanPayment(
            user_id=self.user_id, loan_id=loan.id, installment_number=installment_number,
            payment_date=request.payment_date, amount=request.amount, principal_paid=principal_paid,
            interest_paid=interest_paid, outstanding_after=outstanding_after,
            remaining_installments=next_remaining, bank_account_id=bank_record.id,
            journal_entry_id=entry.id, idempotency_key=request.idempotency_key,
            payload_hash=fingerprint, note=request.note.strip(),
        )
        self.db.add(payment)
        self.db.commit(); self.db.refresh(payment)
        return payment

    def payment_history(self, loan_id: int) -> list[LoanPayment]:
        loan = self.get(loan_id)
        if loan.loan_type == "PRIVATE_FLEXIBLE":
            raise ValueError("Use the private-loan payment history.")
        return self.db.query(LoanPayment).filter_by(user_id=self.user_id, loan_id=loan.id).order_by(LoanPayment.installment_number).all()

    @staticmethod
    def _remaining_installments(loan: Loan) -> int:
        balance, payment = float(loan.outstanding_balance), float(loan.monthly_payment)
        if balance <= 0 or payment <= 0:
            return 0
        rate = float(loan.annual_rate) / 1200
        if rate == 0:
            return min(loan.term_months, ceil(balance / payment))
        ratio = rate * balance / payment
        if ratio >= 1:
            return loan.term_months
        return min(loan.term_months, ceil(-log(1 - ratio) / log(1 + rate)))

    def refinance(self, loan_id: int, request: LoanRefinanceRequest) -> Loan:
        old = self.get(loan_id)
        if old.loan_type == 'PRIVATE_FLEXIBLE':
            raise ValueError('Private loan refinancing is not supported.')
        if old.status != "ACTIVE":
            raise ValueError("Only active loans can be refinanced.")
        old_liability = self.accounts.get_by_code(old.liability_account_code)
        new_code = self.LIABILITY_CODES[request.loan_type]
        new_liability = self.accounts.get_by_code(new_code)
        bank = self.accounts.get_by_code(request.bank_account_code)
        bank_record = self.db.query(BankAccount).filter(BankAccount.id == request.bank_account_id, BankAccount.user_id == self.user_id).first()
        if bank_record is None:
            raise ValueError("Select a valid refinance bank account.")
        fees_account = self.accounts.get_by_code(5790)
        debits = old.outstanding_balance + request.fees
        lines = [JournalLineInput(account_id=old_liability.id, debit=old.outstanding_balance, credit=Decimal("0.00")), JournalLineInput(account_id=new_liability.id, debit=Decimal("0.00"), credit=request.principal_amount)]
        if request.fees:
            lines.append(JournalLineInput(account_id=fees_account.id, debit=request.fees, credit=Decimal("0.00")))
        difference = request.principal_amount - debits
        if difference > 0:
            lines.append(JournalLineInput(account_id=bank.id, debit=difference, credit=Decimal("0.00")))
        elif difference < 0:
            lines.append(JournalLineInput(account_id=bank.id, debit=Decimal("0.00"), credit=-difference))
        entry = self.ledger.post(description=f"Debt purchase: {old.name} to {request.lender}", lines=lines, user_id=self.user_id, related_reference=f"loan-refinance:{old.id}:bank-account:{bank_record.id}")
        bank_record.current_balance += difference
        old.status = "REFINANCED"; old.outstanding_balance = Decimal("0.00")
        new = Loan(user_id=self.user_id, name=f"{old.name} · Refinance", lender=request.lender, loan_type=request.loan_type, principal_amount=request.principal_amount, outstanding_balance=request.principal_amount, amount_received=request.principal_amount-request.fees, fees=request.fees, annual_rate=request.annual_rate, term_months=request.term_months, monthly_payment=request.monthly_payment, first_payment_date=request.first_payment_date, destination_account_code=request.bank_account_code, destination_bank_account_id=bank_record.id, liability_account_code=new_code, journal_entry_id=entry.id, status="ACTIVE")
        self.db.add(new); self.db.commit(); self.db.refresh(new)
        return new
