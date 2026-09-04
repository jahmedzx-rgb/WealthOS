from sqlalchemy.orm import Session

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
