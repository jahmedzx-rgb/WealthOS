from sqlalchemy.orm import Session

from app.accounting.schemas.card_payment import (
    CardPaymentRequest,
)
from app.accounting.services.card_payment_service import (
    CardPaymentService,
)


class CardPaymentUseCase:
    def __init__(self, db: Session, user_id: int = 1):
        self.service = CardPaymentService(db, user_id)

    def execute(
        self,
        request: CardPaymentRequest,
    ):
        return self.service.execute(request)
