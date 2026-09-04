from sqlalchemy.orm import Session

from app.accounting.schemas.income import (
    IncomeRequest,
)
from app.accounting.services.income_service import (
    IncomeService,
)


class IncomeUseCase:
    def __init__(self, db: Session, user_id: int = 1):
        self.service = IncomeService(db, user_id)

    def execute(
        self,
        request: IncomeRequest,
    ):
        return self.service.execute(request)
