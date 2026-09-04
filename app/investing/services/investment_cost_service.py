from decimal import Decimal

from sqlalchemy.orm import Session

from app.investing.repositories.position_repository import PositionRepository


class InvestmentCostService:
    def __init__(self, db: Session):
        self.position_repository = PositionRepository(db)

    def get_cost(
        self,
        portfolio_id: int,
        security_id: int,
    ):
        position = self.position_repository.get(
            portfolio_id,
            security_id,
        )

        if position is None:
            return {
                "quantity": Decimal("0"),
                "total_cost": Decimal("0"),
                "average_cost": Decimal("0"),
            }

        quantity = Decimal(position.quantity)
        average_cost = Decimal(position.average_cost)
        total_cost = quantity * average_cost

        return {
            "quantity": quantity,
            "total_cost": total_cost,
            "average_cost": average_cost,
        }
