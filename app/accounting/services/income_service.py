from sqlalchemy.orm import Session

from app.accounting.schemas.income import (
    IncomeRequest,
)
from app.accounting.services.account_resolver import (
    AccountResolver,
)
from app.accounting.services.funds_transfer_service import (
    FundsTransferService,
)
from app.accounting.models.rental_schedule import RentalSchedule
from app.accounting.models.bank_account import BankAccount
from app.accounting.models.credit_card_account import CreditCardAccount
from app.accounting.services.card_statement_service import statement_view, validate_card_date


class IncomeService:
    def __init__(self, db: Session, user_id: int = 1):
        self.db = db
        self.account_resolver = AccountResolver(db)
        self.funds_transfer_service = (
            FundsTransferService(db, user_id)
        )

    def execute(
        self,
        request: IncomeRequest,
    ):
        destination_account = (
            self.account_resolver.get_by_code(
                int(request.destination_account_code),
            )
        )
        bank_account = None
        credit_card = None
        if request.destination_bank_account_id is not None:
            if destination_account.code != 1120:
                raise ValueError("لا يمكن ربط الحساب البنكي إلا بحسابات البنوك في دفتر الأستاذ.")
            bank_account = self.db.query(BankAccount).filter(BankAccount.id == request.destination_bank_account_id, BankAccount.user_id == self.funds_transfer_service.user_id).first()
            if bank_account is None:
                raise ValueError("لم يتم العثور على حساب الوجهة البنكي المحدد.")

        income_source = (
            request.accounting_category
            or request.income_source
        ).upper()

        if request.destination_credit_card_id is not None:
            if income_source != "CASHBACK":
                raise ValueError("Credit cards can only receive cashback income.")
            if destination_account.code != 2110:
                raise ValueError("Credit card cashback must post to the credit card liability account.")
            credit_card = self.db.query(CreditCardAccount).filter(
                CreditCardAccount.id == request.destination_credit_card_id,
                CreditCardAccount.user_id == self.funds_transfer_service.user_id,
                CreditCardAccount.is_active.is_(True),
            ).with_for_update().first()
            if credit_card is None:
                raise ValueError("The selected credit card was not found.")
            if request.amount > credit_card.current_balance:
                raise ValueError("Cashback cannot exceed the card's outstanding balance.")
            validate_card_date(credit_card, request.transaction_date)

        if income_source == "SALARY":
            income_account = (
                self.account_resolver
                .get_salary_income_account()
            )

        elif income_source == "RENTAL":
            income_account = (
                self.account_resolver
                .get_rental_income_account()
            )

        elif income_source == "DIVIDEND":
            income_account = (
                self.account_resolver
                .get_dividend_income_account()
            )

        elif income_source == "INTEREST":
            income_account = (
                self.account_resolver
                .get_interest_income_account()
            )

        elif income_source == "BUSINESS":
            income_account = (
                self.account_resolver
                .get_business_income_account()
            )

        elif income_source == "CAPITAL_GAIN":
            income_account = (
                self.account_resolver
                .get_realized_gain_account()
            )

        elif income_source == "CASHBACK":
            income_account = (
                self.account_resolver
                .get_cashback_income_account()
            )

        else:
            income_account = (
                self.account_resolver
                .get_other_income_account()
            )

        outstanding_statement = (
            statement_view(self.db, credit_card)["statement_balance"]
            if credit_card is not None
            else None
        )
        entry = self.funds_transfer_service.execute(
            from_account_id=income_account.id,
            to_account_id=destination_account.id,
            amount=request.amount,
            description=request.description,
            transaction_date=request.transaction_date,
            related_reference=(
                f"credit-card-cashback:{credit_card.id}"
                if credit_card is not None
                else request.linked_source
            ),
            auto_commit=False,
        )
        if bank_account is not None:
            bank_account.current_balance += request.amount
        if credit_card is not None:
            credit_card.current_balance -= request.amount
            credit_card.statement_balance = max(outstanding_statement - request.amount, 0)
        if income_source == "RENTAL" and request.linked_source and request.linked_source.startswith("property:") and request.rent_frequency and request.next_rent_due_date:
            schedule = self.db.query(RentalSchedule).filter(
                RentalSchedule.user_id == self.funds_transfer_service.user_id,
                RentalSchedule.property_reference == request.linked_source,
                RentalSchedule.active.is_(True),
            ).first()
            property_name = request.rent_property_name or "Property"
            if schedule is None:
                schedule = RentalSchedule(user_id=self.funds_transfer_service.user_id, property_reference=request.linked_source, property_name=property_name)
                self.db.add(schedule)
            schedule.property_name = property_name
            schedule.expected_amount = request.amount
            schedule.frequency = request.rent_frequency
            schedule.next_due_date = request.next_rent_due_date
            schedule.destination_account_code = request.destination_account_code
        self.db.commit()
        self.db.refresh(entry)
        return entry
