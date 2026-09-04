from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.models.loan import Loan
from app.accounting.models.bank_account import BankAccount
from app.accounting.schemas.journal import JournalLineInput
from app.accounting.schemas.loan import LoanRequest, LoanRefinanceRequest, LoanSettlementRequest, LoanUpdateRequest
from app.accounting.services.account_resolver import AccountResolver
from app.accounting.services.ledger_service import LedgerService


class LoanService:
    LIABILITY_CODES = {"SHORT_TERM": 2140, "LONG_TERM": 2220, "MORTGAGE": 2210}

    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.accounts = AccountResolver(db)
        self.ledger = LedgerService(db)
        self.user_id = user_id

    def create(self, request: LoanRequest) -> Loan:
        bank = self.accounts.get_by_code(request.destination_account_code)
        bank_record = self.db.query(BankAccount).filter(BankAccount.id == request.destination_bank_account_id, BankAccount.user_id == self.user_id).first()
        if bank_record is None:
            raise ValueError("Select a valid destination bank account.")
        liability_code = self.LIABILITY_CODES[request.loan_type]
        liability = self.accounts.get_by_code(liability_code)
        lines = [
            JournalLineInput(account_id=bank.id, debit=request.amount_received, credit=Decimal("0.00")),
            JournalLineInput(account_id=liability.id, debit=Decimal("0.00"), credit=request.principal_amount),
        ]
        if request.fees:
            fees = self.accounts.get_by_code(5790)
            lines.insert(1, JournalLineInput(account_id=fees.id, debit=request.fees, credit=Decimal("0.00")))
        entry = self.ledger.post(description=f"New loan: {request.name}", lines=lines, user_id=self.user_id, related_reference=f"loan-funding:bank-account:{bank_record.id}")
        loan = Loan(**request.model_dump(), user_id=self.user_id, liability_account_code=liability_code, outstanding_balance=request.principal_amount, journal_entry_id=entry.id)
        self.db.add(loan)
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
        if loan.status != "ACTIVE":
            raise ValueError("Only active loans can be edited.")
        for field, value in request.model_dump().items():
            setattr(loan, field, value)
        self.db.commit(); self.db.refresh(loan)
        return loan

    def void(self, loan_id: int) -> Loan:
        loan = self.get(loan_id)
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

    def refinance(self, loan_id: int, request: LoanRefinanceRequest) -> Loan:
        old = self.get(loan_id)
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
