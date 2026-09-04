from sqlalchemy.orm import Session

from app.accounting.application.withdraw_cash_service import (
    WithdrawCashService,
)
from app.accounting.schemas.withdraw_cash import (
    WithdrawCashRequest,
)


class WithdrawCashUseCase:
    def __init__(self, db: Session, user_id: int = 1):
        self.service = WithdrawCashService(db, user_id)

    def execute(
        self,
        request: WithdrawCashRequest,
    ):
        return self.service.execute(request)
