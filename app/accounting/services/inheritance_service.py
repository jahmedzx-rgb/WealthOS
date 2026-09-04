from sqlalchemy.orm import Session

from app.accounting.models import Account, BankAccount, JournalEntry, JournalLine
from app.accounting.models.property_asset import PropertyAsset
from app.accounting.schemas.inheritance import InheritanceRequest


class InheritanceService:
    ASSET_CODES = {
        "CASH_ON_HAND": 1110,
        "BANK_ACCOUNT": 1120,
        "PROPERTY": 1210,
        "VEHICLE": 1220,
        "INVESTMENT": 1390,
        "OTHER_ASSET": 1290,
    }

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def execute(self, request: InheritanceRequest):
        asset_account = self.db.query(Account).filter(Account.code == self.ASSET_CODES[request.asset_type]).first()
        equity_code = 3150 if request.timing == "BEFORE_WEALTHOS" else 3260
        equity_account = self.db.query(Account).filter(Account.code == equity_code).first()
        if asset_account is None or equity_account is None:
            raise ValueError("The inheritance ledger accounts are not configured.")

        bank = None
        if request.asset_type == "BANK_ACCOUNT":
            bank = self.db.query(BankAccount).filter(BankAccount.id == request.bank_account_id, BankAccount.user_id == self.user_id).first()
            if bank is None:
                raise ValueError("The selected bank account was not found.")

        timing_label = "owned before WealthOS" if request.timing == "BEFORE_WEALTHOS" else "received after WealthOS started"
        entry = JournalEntry(user_id=self.user_id, description=f"Inheritance · {request.description.strip()} · {timing_label}", transaction_date=request.transaction_date)
        self.db.add(entry)
        self.db.flush()
        reference_prefix = "opening-inheritance" if request.timing == "BEFORE_WEALTHOS" else "inheritance"
        entry.related_reference = f"{reference_prefix}:{entry.id}"
        self.db.add_all([
            JournalLine(journal_entry_id=entry.id, account_id=asset_account.id, debit=request.amount, credit=0),
            JournalLine(journal_entry_id=entry.id, account_id=equity_account.id, debit=0, credit=request.amount),
        ])
        if bank is not None:
            bank.current_balance += request.amount
        if request.asset_type == "PROPERTY":
            self.db.add(PropertyAsset(user_id=self.user_id, acquisition_journal_entry_id=entry.id, name=request.asset_name.strip(), usage=request.property_usage, income_type=request.property_income_type if request.property_usage == "INVESTMENT_PROPERTY" else None, current_value=request.amount))
        self.db.commit()
        self.db.refresh(entry)
        return {"message": "Inheritance recorded successfully.", "journal_entry_id": entry.id, "related_reference": entry.related_reference}
