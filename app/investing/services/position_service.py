from decimal import Decimal

from sqlalchemy.orm import Session

from app.investing.models.position import Position
from app.investing.repositories.position_repository import (
    PositionRepository,
)


class PositionService:
    def __init__(self, db: Session):
        self.db = db
        self.position_repository = PositionRepository(db)

    def get_position(
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
                "average_cost": Decimal("0"),
            }

        return {
            "quantity": position.quantity,
            "average_cost": position.average_cost,
        }

    def get(
        self,
        portfolio_id: int,
        security_id: int,
    ) -> Position:
        position = self.position_repository.get(
            portfolio_id,
            security_id,
        )

        if position is None:
            raise ValueError("Position not found.")

        return position

    def list_by_portfolio(
        self,
        portfolio_id: int,
    ) -> list[Position]:
        return self.position_repository.list_by_portfolio(
            portfolio_id
        )

    def validate_sell(
        self,
        portfolio_id: int,
        security_id: int,
        quantity: Decimal,
    ) -> Position:
        if quantity <= Decimal("0"):
            raise ValueError(
                "Quantity must be greater than zero."
            )

        position = self.position_repository.get(
            portfolio_id,
            security_id,
        )

        if position is None:
            raise ValueError("Position not found.")

        if quantity > position.quantity:
            raise ValueError(
                "Insufficient position quantity."
            )

        return position

    def update_buy(
        self,
        portfolio_id: int,
        security_id: int,
        quantity: Decimal,
        price: Decimal,
    ) -> Position:
        position = self.position_repository.get(
            portfolio_id,
            security_id,
        )

        if position is None:
            position = Position(
                portfolio_id=portfolio_id,
                security_id=security_id,
                quantity=quantity,
                average_cost=price,
            )

            self.position_repository.add(position)

            return position

        total_cost = (
            position.quantity * position.average_cost
        ) + (
            quantity * price
        )

        total_quantity = position.quantity + quantity

        position.quantity = total_quantity
        position.average_cost = (
            total_cost / total_quantity
        )

        return position

    def update_sell(
        self,
        portfolio_id: int,
        security_id: int,
        quantity: Decimal,
    ) -> Position:
        position = self.validate_sell(
            portfolio_id=portfolio_id,
            security_id=security_id,
            quantity=quantity,
        )

        position.quantity -= quantity

        if position.quantity == Decimal("0"):
            position.average_cost = Decimal("0")

        return position
