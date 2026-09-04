from sqlalchemy.orm import Session

from app.investing.repositories.trade_repository import (
    TradeRepository,
)


class TradeService:
    def __init__(self, db: Session):
        self.trade_repository = TradeRepository(db)

    def list_by_position(
        self,
        portfolio_id: int,
        security_id: int,
    ):
        return self.trade_repository.list_by_position(
            portfolio_id=portfolio_id,
            security_id=security_id,
        )
