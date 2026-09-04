from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.models import Account, AlternativeInvestment, BankAccount, JournalEntry, JournalLine, SavingCircle
from app.accounting.schemas.wealth_products import AlternativeInvestmentRequest, SavingCircleRequest


class WealthProductService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def _bank(self, bank_id: int, amount: Decimal, currency_code: str = "SAR") -> BankAccount:
        bank = self.db.query(BankAccount).filter(BankAccount.id == bank_id, BankAccount.user_id == self.user_id).first()
        if bank is None:
            raise ValueError("Funding bank account was not found.")
        if bank.currency_code != currency_code:
            raise ValueError("The bank account and investment currencies must match.")
        if bank.current_balance < amount:
            raise ValueError("The selected bank account does not have sufficient funds.")
        return bank

    def _post(self, bank: BankAccount, asset_code: int, amount: Decimal, description: str, transaction_date, reference: str):
        asset = self.db.query(Account).filter(Account.code == asset_code).one()
        cash = self.db.query(Account).filter(Account.code == 1120).one()
        entry = JournalEntry(user_id=self.user_id, description=description, transaction_date=transaction_date, related_reference=reference)
        self.db.add(entry); self.db.flush()
        self.db.add_all([
            JournalLine(journal_entry_id=entry.id, account_id=asset.id, debit=amount, credit=0),
            JournalLine(journal_entry_id=entry.id, account_id=cash.id, debit=0, credit=amount),
        ])
        bank.current_balance -= amount

    def create_saving_circle(self, request: SavingCircleRequest) -> SavingCircle:
        initial = request.installment_amount * request.installments_paid
        bank = self._bank(request.funding_bank_account_id, initial) if initial else self._bank(request.funding_bank_account_id, Decimal("0"))
        item = SavingCircle(user_id=self.user_id, **request.model_dump(exclude={"transaction_date"}))
        self.db.add(item); self.db.flush()
        if initial:
            self._post(bank, 1170, initial, f"Saving Circle · {item.circle_name} · {item.installments_paid} installments", request.transaction_date, f"saving-circle:{item.id}")
        self.db.commit(); self.db.refresh(item)
        return item

    def create_alternative(self, request: AlternativeInvestmentRequest) -> AlternativeInvestment:
        bank = self._bank(request.funding_bank_account_id, request.principal_amount, request.currency_code.upper())
        data = request.model_dump(exclude={"transaction_date"})
        data["currency_code"] = request.currency_code.upper()
        item = AlternativeInvestment(user_id=self.user_id, **data, current_value=request.principal_amount)
        self.db.add(item); self.db.flush()
        asset_code = 1380 if request.investment_type in {"DEBT_CROWDFUNDING", "EQUITY_CROWDFUNDING", "REAL_ESTATE_CROWDFUNDING", "P2P_LENDING"} else 1390
        self._post(bank, asset_code, request.principal_amount, f"Alternative Investment · {item.investment_name} · {item.platform_name}", request.transaction_date, f"alternative-investment:{item.id}")
        self.db.commit(); self.db.refresh(item)
        return item
