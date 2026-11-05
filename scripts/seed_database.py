from collections.abc import Callable

from sqlalchemy.orm import Session

from app.accounting.models.account import Account
from app.core.models.currency import Currency
from app.core.models.entity import Entity
from app.database.engine import SessionLocal
from app.investing.models.broker import Broker
from app.investing.models.portfolio import Portfolio
from app.investing.models.portfolio_objective import PortfolioObjective
from app.investing.models.portfolio_strategy import PortfolioStrategy
from app.investing.models.security import Security

from scripts.seed_chart_of_accounts import build_accounts
from scripts.seeds.seed_brokers import seed_brokers
from scripts.seeds.seed_currencies import seed_currencies
from scripts.seeds.seed_entities import seed_entities
from scripts.seeds.seed_portfolio_objectives import (
    seed_portfolio_objectives,
)
from scripts.seeds.seed_portfolio_strategies import (
    seed_portfolio_strategies,
)
from scripts.seeds.seed_portfolios import seed_portfolios
from scripts.seeds.seed_securities import seed_securities


def seed_if_empty(
    db: Session,
    model,
    seed_function: Callable[[Session], None],
    label: str,
) -> None:
    exists = db.query(model).first() is not None

    if exists:
        print(f"Skipped {label}: data already exists.")
        return

    seed_function(db)
    db.flush()

    print(f"Seeded {label}.")


def seed_accounts(db: Session) -> None:
    db.add_all(build_accounts())


def main() -> None:
    db = SessionLocal()

    try:
        seed_if_empty(
            db,
            Currency,
            seed_currencies,
            "currencies",
        )

        seed_if_empty(
            db,
            Entity,
            seed_entities,
            "entities",
        )

        seed_if_empty(
            db,
            Broker,
            seed_brokers,
            "brokers",
        )

        seed_if_empty(
            db,
            PortfolioStrategy,
            seed_portfolio_strategies,
            "portfolio strategies",
        )

        seed_if_empty(
            db,
            PortfolioObjective,
            seed_portfolio_objectives,
            "portfolio objectives",
        )

        seed_if_empty(
            db,
            Portfolio,
            seed_portfolios,
            "portfolios",
        )

        seed_if_empty(
            db,
            Security,
            seed_securities,
            "securities",
        )

        seed_if_empty(
            db,
            Account,
            seed_accounts,
            "chart of accounts",
        )

        db.commit()

        print("Database seed completed successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
