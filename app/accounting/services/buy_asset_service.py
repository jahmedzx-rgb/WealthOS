from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.accounting.models import Account, BankAccount, JournalEntry, JournalLine
from app.accounting.schemas.buy_asset import BuyAssetRequest


class BuyAssetService:
    ALLOWED_ASSET_CODES = {1150, 1220, 1230}

    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.user_id = user_id

    def execute(self, request: BuyAssetRequest):
        if request.asset_account_code not in self.ALLOWED_ASSET_CODES:
            raise ValueError("The selected asset type is not supported by this operation.")
        asset_account = self.db.query(Account).filter(Account.code == request.asset_account_code).first()
        payment_code = 1120 if request.payment_source == "BANK_ACCOUNT" else 1110
        payment_account = self.db.query(Account).filter(Account.code == payment_code).first()
        if asset_account is None or payment_account is None:
            raise ValueError("The asset or payment ledger account is not configured.")

        bank = None
        if request.payment_source == "BANK_ACCOUNT":
            bank = self.db.query(BankAccount).filter(BankAccount.id == request.bank_account_id, BankAccount.user_id == self.user_id).first()
            if bank is None:
                raise ValueError("The selected bank account was not found.")
            available = bank.current_balance
            currency = bank.currency_code
            reference = f"asset-purchase:{request.asset_account_code}:bank-account:{bank.id}"
        else:
            available = self.db.query(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0)).join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id).filter(JournalEntry.user_id == self.user_id, JournalLine.account_id == payment_account.id).scalar() or Decimal("0")
            currency = "SAR"
            reference = f"asset-purchase:{request.asset_account_code}:cash-on-hand"
        if request.amount > available:
            raise ValueError(f"Purchase amount exceeds the available balance of {available:.2f} {currency}.")

        entry = JournalEntry(user_id=self.user_id, description=request.description, transaction_date=request.transaction_date, related_reference=reference)
        self.db.add(entry)
        self.db.flush()
        self.db.add_all([
            JournalLine(journal_entry_id=entry.id, account_id=asset_account.id, debit=request.amount, credit=0),
            JournalLine(journal_entry_id=entry.id, account_id=payment_account.id, debit=0, credit=request.amount),
        ])
        if bank is not None:
            bank.current_balance -= request.amount
        self.db.commit()
        self.db.refresh(entry)
        return entry
