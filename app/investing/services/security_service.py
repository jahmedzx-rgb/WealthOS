from sqlalchemy.orm import Session

from app.investing.models.security import Security
from app.investing.repositories.security_repository import (
    SecurityRepository,
)


class SecurityService:
    def __init__(self, db: Session):
        self.security_repository = SecurityRepository(db)

    def get(
        self,
        security_id: int,
    ) -> Security:
        security = self.security_repository.get(
            security_id
        )

        if security is None:
            raise ValueError(
                f"Security {security_id} not found."
            )

        return security

    def get_by_symbol(
        self,
        symbol: str,
    ) -> Security:
        security = (
            self.security_repository.get_by_symbol(
                symbol
            )
        )

        if security is None:
            raise ValueError(
                f"Security '{symbol}' not found."
            )

        return security

    def list(self) -> list[Security]:
        return self.security_repository.list()
