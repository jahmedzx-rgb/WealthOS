from sqlalchemy.orm import Session

from app.accounting.schemas.card_payment import (
    CardPaymentRequest,
)
from app.accounting.services.account_resolver import (
    AccountResolver,
)
from app.accounting.services.funds_transfer_service import (
    FundsTransferService,
)
from app.accounting.models.credit_card_account import CreditCardAccount
from app.accounting.models.bank_account import BankAccount


class CardPaymentService:
    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.user_id = user_id
        self.account_resolver = AccountResolver(db)
        self.funds_transfer_service = (
            FundsTransferService(db, user_id)
        )

    def execute(
        self,
        request: CardPaymentRequest,
    ):
        card = self.db.query(CreditCardAccount).filter(
            CreditCardAccount.id == request.credit_card_id,
            CreditCardAccount.user_id == self.user_id,
            CreditCardAccount.is_active.is_(True),
        ).first()
        if card is None:
            raise ValueError("لم يتم العثور على البطاقة الائتمانية.")
        if request.amount > card.current_balance:
            raise ValueError("لا يمكن أن يتجاوز السداد الرصيد الحالي للبطاقة.")
        bank = self.db.query(BankAccount).filter(
            BankAccount.id == request.bank_account_id,
            BankAccount.user_id == self.user_id,
        ).first()
        if bank is None:
            raise ValueError("لم يتم العثور على الحساب البنكي.")
        if request.amount > bank.current_balance:
            raise ValueError("يتجاوز السداد رصيد الحساب البنكي المحدد.")
        payment_account = (
            self.account_resolver.get_by_code(
                request.payment_account_code,
            )
        )

        credit_card_account = (
            self.account_resolver.get_by_code(
                request.credit_card_account_code,
            )
        )

        entry = self.funds_transfer_service.execute(
            from_account_id=payment_account.id,
            to_account_id=credit_card_account.id,
            amount=request.amount,
            description=request.description,
            transaction_date=request.transaction_date,
            related_reference=f"credit-card-payment:{card.id}",
            auto_commit=False,
        )
        card.current_balance -= request.amount
        card.statement_balance = max(card.statement_balance - request.amount, 0)
        bank.current_balance -= request.amount
        self.db.commit()
        self.db.refresh(entry)
        return entry
