from sqlalchemy.orm import Session

from app.accounting.application.transfer_service import (
    TransferService,
)
from app.accounting.schemas.transfer import (
    TransferRequest,
)


class TransferUseCase:
    def __init__(self, db: Session, user_id: int = 1):
        self.service = TransferService(db, user_id)

    def execute(
        self,
        request: TransferRequest,
    ):
        return self.service.execute(request)
