from sqlalchemy.orm import Session

from app.accounting.schemas.buy_property import (
    BuyPropertyRequest,
)
from app.accounting.services.buy_property_service import (
    BuyPropertyService,
)


class BuyPropertyUseCase:
    def __init__(self, db: Session, user_id: int = 1):
        self.service = BuyPropertyService(db, user_id)

    def execute(
        self,
        request: BuyPropertyRequest,
    ):
        return self.service.execute(request)
