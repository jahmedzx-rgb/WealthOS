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
from app.accounting.services.card_statement_service import validate_card_date, statement_view


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
        ).with_for_update().first()
        if card is None:
            raise ValueError("لم يتم العثور على البطاقة الائتمانية.")
        validate_card_date(card, request.transaction_date)
        outstanding_statement = statement_view(self.db, card)['statement_balance']
        bank = None
        source_card = None
        source_statement = None
        if request.bank_account_id is not None:
            bank = self.db.query(BankAccount).filter(
                BankAccount.id == request.bank_account_id,
                BankAccount.user_id == self.user_id,
            ).first()
            if bank is None:
                raise ValueError("The selected bank account was not found.")
            if request.amount > bank.current_balance:
                raise ValueError("The payment exceeds the selected bank account balance.")
        else:
            if request.payment_credit_card_id == request.credit_card_id:
                raise ValueError("The payment card must be different from the card being paid.")
            source_card = self.db.query(CreditCardAccount).filter(
                CreditCardAccount.id == request.payment_credit_card_id,
                CreditCardAccount.user_id == self.user_id,
                CreditCardAccount.is_active.is_(True),
            ).with_for_update().first()
            if source_card is None:
                raise ValueError("The selected payment card was not found.")
            validate_card_date(source_card, request.transaction_date)
            if source_card.current_balance + request.amount > source_card.credit_limit:
                raise ValueError("The SADAD payment exceeds the source card's available credit.")
            source_statement = statement_view(self.db, source_card)['statement_balance']
        payment_account = self.account_resolver.get_by_code(2110 if source_card is not None else request.payment_account_code)

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
            related_reference=(f"credit-card-sadad:{source_card.id}:{card.id}" if source_card is not None else f"credit-card-payment:{card.id}"),
            auto_commit=False,
        )
        card.current_balance -= request.amount
        card.statement_balance = max(outstanding_statement - request.amount, 0)
        if bank is not None:
            bank.current_balance -= request.amount
        if source_card is not None:
            source_card.current_balance += request.amount
            # Funding another card is new spending on the source card. It raises
            # current debt, but must not be added to an already-issued statement.
            source_card.statement_balance = source_statement
        self.db.commit()
        self.db.refresh(entry)
        return entry
