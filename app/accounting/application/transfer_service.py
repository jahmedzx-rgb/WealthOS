from sqlalchemy.orm import Session
from sqlalchemy import func

from app.accounting.schemas.transfer import (
    TransferRequest,
)
from app.accounting.services.account_resolver import (
    AccountResolver,
)
from app.accounting.services.funds_transfer_service import (
    FundsTransferService,
)
from app.accounting.models import BankAccount, JournalEntry, JournalLine


class TransferService:
    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.account_resolver = AccountResolver(db)
        self.funds_transfer_service = (
            FundsTransferService(db, user_id)
        )

    def execute(
        self,
        request: TransferRequest,
    ):
        from_account = (
            self.account_resolver.get_by_code(
                request.from_account_code,
            )
        )

        to_account = (
            self.account_resolver.get_by_code(
                request.to_account_code,
            )
        )
        from_bank = None
        to_bank = None
        if request.from_account_code == 1120:
            if request.from_bank_account_id is None:
                raise ValueError("اختر الحساب البنكي المصدر.")
            from_bank = self.db.query(BankAccount).filter(BankAccount.id == request.from_bank_account_id, BankAccount.user_id == self.funds_transfer_service.user_id).first()
            if from_bank is None:
                raise ValueError("لم يتم العثور على الحساب البنكي المصدر.")
            if from_bank.current_balance < request.amount:
                raise ValueError("لا يحتوي الحساب البنكي المصدر على رصيد كافٍ.")
        if request.to_account_code == 1120:
            if request.to_bank_account_id is None:
                raise ValueError("اختر الحساب البنكي الوجهة.")
            to_bank = self.db.query(BankAccount).filter(BankAccount.id == request.to_bank_account_id, BankAccount.user_id == self.funds_transfer_service.user_id).first()
            if to_bank is None:
                raise ValueError("لم يتم العثور على الحساب البنكي الوجهة.")
        if from_bank and to_bank:
            if from_bank.id == to_bank.id:
                raise ValueError("يجب أن يختلف الحساب البنكي المصدر عن الوجهة.")
            if from_bank.currency_code != to_bank.currency_code:
                raise ValueError("تتطلب التحويلات البنكية المباشرة تطابق العملات.")
        if request.from_account_code != 1120:
            available = self.db.query(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0)).join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id).filter(JournalEntry.user_id == self.funds_transfer_service.user_id, JournalLine.account_id == from_account.id).scalar()
            if request.amount > available:
                raise ValueError("لا يحتوي الحساب المصدر على رصيد كافٍ.")

        entry = self.funds_transfer_service.execute(
            from_account_id=from_account.id,
            to_account_id=to_account.id,
            amount=request.amount,
            description=request.description,
            transaction_date=request.transaction_date,
            related_reference=f"account-transfer:{request.from_account_code}:{request.to_account_code}",
            auto_commit=False,
        )
        if from_bank:
            from_bank.current_balance -= request.amount
        if to_bank:
            to_bank.current_balance += request.amount
        self.db.commit()
        return entry
