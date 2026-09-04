from sqlalchemy.orm import Session

from app.accounting.models import Account, BankAccount, JournalEntry, JournalLine, PropertyAsset
from app.accounting.schemas.expense import ExpenseRequest


class ExpenseService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def execute(self, request: ExpenseRequest):
        expense_account = self.db.query(Account).filter(
            Account.code == request.expense_account_code,
            Account.account_type == "EXPENSE",
        ).first()
        bank_ledger = self.db.query(Account).filter(Account.code == 1120).first()
        if expense_account is None or bank_ledger is None:
            raise ValueError("فئة المصروف المحددة غير مهيأة.")

        bank = self.db.query(BankAccount).filter(
            BankAccount.id == request.payment_bank_account_id,
            BankAccount.user_id == self.user_id,
        ).first()
        if bank is None:
            raise ValueError("لم يتم العثور على حساب السداد المحدد.")
        if request.amount > bank.current_balance:
            raise ValueError(
                f"Expense amount exceeds the available balance of {bank.current_balance:.2f} {bank.currency_code}."
            )

        property_asset = None
        if request.property_id is not None:
            property_asset = self.db.query(PropertyAsset).filter(
                PropertyAsset.id == request.property_id,
                PropertyAsset.user_id == self.user_id,
                PropertyAsset.status == "ACTIVE",
            ).first()
            if property_asset is None:
                raise ValueError("لم يتم العثور على العقار المحدد.")

        reference = (
            f"property-expense:{property_asset.id}"
            if property_asset is not None
            else f"bank-expense:{bank.id}"
        )
        entry = JournalEntry(
            user_id=self.user_id,
            description=request.description.strip(),
            transaction_date=request.transaction_date,
            related_reference=reference,
        )
        self.db.add(entry)
        self.db.flush()
        self.db.add_all([
            JournalLine(journal_entry_id=entry.id, account_id=expense_account.id, debit=request.amount, credit=0),
            JournalLine(journal_entry_id=entry.id, account_id=bank_ledger.id, debit=0, credit=request.amount),
        ])
        bank.current_balance -= request.amount
        self.db.commit()
        self.db.refresh(entry)
        return entry
