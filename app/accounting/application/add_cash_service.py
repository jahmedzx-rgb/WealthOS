from sqlalchemy.orm import Session

from app.accounting.schemas.add_cash import (
    AddCashRequest,
)
from app.accounting.services.account_resolver import (
    AccountResolver,
)
from app.accounting.services.funds_transfer_service import (
    FundsTransferService,
)
from app.investing.services.portfolio_service import PortfolioService
from app.accounting.models.bank_account import BankAccount


class AddCashService:
    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.account_resolver = AccountResolver(db)
        self.funds_transfer_service = (
            FundsTransferService(db, user_id)
        )

    def execute(
        self,
        request: AddCashRequest,
    ):
        portfolio = PortfolioService(self.db).get(request.portfolio_id, self.funds_transfer_service.user_id)
        bank = self.db.query(BankAccount).filter(
            BankAccount.id == request.source_bank_account_id,
            BankAccount.user_id == self.funds_transfer_service.user_id,
        ).with_for_update().first()
        if bank is None:
            raise ValueError("اختر حساب مصدر بنكيًا صالحًا.")
        if bank.current_balance < request.amount:
            raise ValueError(f"الرصيد البنكي غير كافٍ. المتاح: {bank.current_balance:.2f} {bank.currency_code}.")
        if bank.currency_code != portfolio.base_currency.code:
            raise ValueError("يجب أن تتطابق عملتا الحساب البنكي والمحفظة للتمويل المباشر.")
        brokerage_cash = (
            self.account_resolver
            .get_brokerage_cash_account()
        )

        bank_account = (
            self.account_resolver
            .get_bank_account()
        )

        entry = self.funds_transfer_service.execute(
            from_account_id=bank_account.id,
            to_account_id=brokerage_cash.id,
            amount=request.amount,
            description=request.description,
            transaction_date=request.transaction_date,
            related_reference=f"portfolio-funding:{portfolio.id}:bank-account:{bank.id}",
            auto_commit=False,
        )
        bank.current_balance -= request.amount
        portfolio.cash_balance += request.amount
        self.db.commit()
        self.db.refresh(portfolio)
        return entry
