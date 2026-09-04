from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.accounting.models import Account, BankAccount, JournalEntry, JournalLine
from app.accounting.schemas.buy_property import BuyPropertyRequest
from app.accounting.models.property_asset import PropertyAsset


class BuyPropertyService:
    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.user_id = user_id

    def execute(self, request: BuyPropertyRequest):
        total_cost = request.amount + request.transfer_tax
        property_account = self.db.query(Account).filter(Account.code == request.property_account_code).first()
        payment_code = 1120 if request.payment_source == "BANK_ACCOUNT" else 1110
        payment_ledger = self.db.query(Account).filter(Account.code == payment_code).first()
        if property_account is None or payment_ledger is None:
            raise ValueError("حساب العقار أو السداد في دفتر الأستاذ غير مهيأ.")

        bank = None
        if request.payment_source == "BANK_ACCOUNT":
            bank = self.db.query(BankAccount).filter(BankAccount.id == request.bank_account_id, BankAccount.user_id == self.user_id).first()
            if bank is None:
                raise ValueError("لم يتم العثور على الحساب البنكي المحدد.")
            available_balance = bank.current_balance
            currency = bank.currency_code
            related_reference = f"property-purchase:bank-account:{bank.id}"
        else:
            available_balance = self.db.query(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0)).join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id).filter(JournalEntry.user_id == self.user_id, JournalLine.account_id == payment_ledger.id).scalar() or Decimal("0")
            currency = "SAR"
            related_reference = "property-purchase:cash-on-hand"
        if total_cost > available_balance:
            raise ValueError(f"إجمالي الشراء شامل الضريبة يتجاوز الرصيد المتاح {available_balance:.2f} {currency}.")

        entry = JournalEntry(
            user_id=self.user_id,
            description=request.description,
            transaction_date=request.transaction_date,
            related_reference=related_reference,
        )
        self.db.add(entry)
        self.db.flush()
        self.db.add_all([
            JournalLine(journal_entry_id=entry.id, account_id=property_account.id, debit=total_cost, credit=0),
            JournalLine(journal_entry_id=entry.id, account_id=payment_ledger.id, debit=0, credit=total_cost),
        ])
        property_name = request.property_name or request.description.removeprefix("Property Purchase:").split(" · Transfer Tax", 1)[0].strip() or "Property"
        self.db.add(PropertyAsset(user_id=self.user_id, acquisition_journal_entry_id=entry.id, name=property_name, usage=request.property_usage, income_type=request.property_income_type, current_value=total_cost))
        if bank is not None:
            bank.current_balance -= total_cost
        self.db.commit()
        self.db.refresh(entry)
        return entry
