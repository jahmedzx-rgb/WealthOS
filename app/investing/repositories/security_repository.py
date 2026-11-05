from sqlalchemy.orm import Session

from app.investing.models.position import Position
from app.investing.models.security import Security


class SecurityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(
        self,
        security_id: int,
    ) -> Security | None:
        return (
            self.db.query(Security)
            .filter(Security.id == security_id)
            .first()
        )

    def get_by_symbol(
        self,
        symbol: str,
    ) -> Security | None:
        return (
            self.db.query(Security)
            .filter(
                Security.symbol == symbol.upper(),
            )
            .first()
        )

    def list(self) -> list[Security]:
        return (
            self.db.query(Security)
            .order_by(Security.symbol)
            .all()
        )

    def list_active_held(self) -> list[Security]:
        """List securities with a non-zero position, excluding unused catalog entries."""
        return (
            self.db.query(Security)
            .join(Position, Position.security_id == Security.id)
            .filter(Security.is_active.is_(True), Position.quantity != 0)
            .distinct()
            .order_by(Security.symbol)
            .all()
        )

    def list_active_by_ids(self, security_ids: set[int]) -> list[Security]:
        if not security_ids:
            return []
        return (
            self.db.query(Security)
            .filter(Security.id.in_(security_ids), Security.is_active.is_(True))
            .order_by(Security.symbol)
            .all()
        )
