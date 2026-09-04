from sqlalchemy.orm import Session

from app.investing.models.position import Position


class PositionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(
        self,
        portfolio_id: int,
        security_id: int,
    ) -> Position | None:
        return (
            self.db.query(Position)
            .filter(
                Position.portfolio_id == portfolio_id,
                Position.security_id == security_id,
            )
            .first()
        )

    def list_by_portfolio(
        self,
        portfolio_id: int,
    ) -> list[Position]:
        return (
            self.db.query(Position)
            .filter(
                Position.portfolio_id == portfolio_id,
                Position.quantity > 0,
            )
            .order_by(Position.security_id)
            .all()
        )

    def add(
        self,
        position: Position,
    ) -> None:
        self.db.add(position)
