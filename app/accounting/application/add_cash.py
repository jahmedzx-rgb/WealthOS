from sqlalchemy.orm import Session

from app.accounting.application.add_cash_service import (
    AddCashService,
)
from app.accounting.schemas.add_cash import (
    AddCashRequest,
)


class AddCashUseCase:
    def __init__(self, db: Session, user_id: int = 1):
        self.service = AddCashService(db, user_id)

    def execute(
        self,
        request: AddCashRequest,
    ):
        return self.service.execute(request)
