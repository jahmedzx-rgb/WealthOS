from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.orm import Session
from decimal import Decimal

from app.database.engine import get_db
from app.investing.application.portfolio_engine import PortfolioEngine
from app.investing.services.portfolio_service import (
    PortfolioService,
)
from app.investing.services.exchange_rate_service import ExchangeRateService
from app.investing.services.portfolio_history_service import PortfolioHistoryService
from app.api.v1.account import current_user
from app.core.models.user import User
from app.core.models.currency import Currency
from app.investing.models.trade import Trade
from app.investing.models.position import Position
from app.investing.models.security import Security
from app.investing.services.opening_portfolio_service import OpeningPortfolioService
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.schemas.journal import JournalLineInput
from app.accounting.services.account_resolver import AccountResolver
from app.accounting.services.ledger_service import LedgerService


router = APIRouter()


class PortfolioCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    broker_id: int = Field(gt=0)
    portfolio_number: str = Field(min_length=2, max_length=80)
    iban: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)


class PortfolioCurrencyUpdateRequest(BaseModel):
    currency_code: str = Field(min_length=3, max_length=3)


class PortfolioUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    portfolio_number: str | None = Field(default=None, min_length=2, max_length=80)
    iban: str | None = Field(default=None, max_length=80)
    currency_code: str = Field(min_length=3, max_length=3)


class PositionUpdateRequest(BaseModel):
    fair_value: Decimal | None = Field(default=None, gt=0)
    distribution_frequency: str | None = Field(default=None, pattern="^(WEEKLY|MONTHLY|QUARTERLY|SEMI_ANNUAL|ANNUAL|IRREGULAR)$")


class OpeningPositionRequest(BaseModel):
    security_id: int = Field(gt=0)
    quantity: Decimal
    total_cost: Decimal
    market_price: Decimal = Field(gt=0)


class OpeningPortfolioRequest(BaseModel):
    cash_balance: Decimal = Field(default=Decimal("0"), ge=0)
    as_of_date: datetime
    positions: list[OpeningPositionRequest] = Field(min_length=1)


class ReinvestedDistributionRequest(BaseModel):
    security_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0)
    transaction_date: datetime


def _consolidated_summary(db: Session, user_id: int):
    portfolios = PortfolioService(db).list(user_id)
    summaries = [(portfolio, PortfolioEngine(db).get_summary(portfolio.id)) for portfolio in portfolios]
    positions = [{**position, "portfolio_id": portfolio.id} for portfolio, item in summaries for position in item["positions"]]
    exchange_rates = ExchangeRateService()
    for position in positions:
        source_currency = position["currency_code"]
        position["total_cost_base"] = exchange_rates.convert(Decimal(str(position["total_cost"])), source_currency, "SAR")
        position["market_value_base"] = exchange_rates.convert(Decimal(str(position["market_value"])), source_currency, "SAR")
        position["unrealized_pl_base"] = position["market_value_base"] - position["total_cost_base"]
    total_cost = sum((Decimal(str(position["total_cost_base"])) for position in positions), Decimal("0"))
    market_value = sum((Decimal(str(position["market_value_base"])) for position in positions), Decimal("0"))
    unrealized_pl = market_value - total_cost
    percentage = (unrealized_pl / total_cost * 100) if total_cost else Decimal("0")
    allocation_summary: dict[str, Decimal] = {}
    for position in positions:
        value = Decimal(str(position.get("market_value_base", position["market_value"])))
        position["weight"] = (value / market_value) if market_value else Decimal("0")
        kind = position.get("allocation_type", position["security_type"])
        allocation_summary[kind] = allocation_summary.get(kind, Decimal("0")) + position["weight"]
    return {
        "portfolio": {"id": 0, "code": "CONSOLIDATED", "name": "All Investments", "base_currency_id": None, "base_currency_code": "SAR", "cash_balance": sum((portfolio.cash_balance for portfolio in portfolios), Decimal("0"))},
        "summary": {"positions_count": len(positions), "total_cost": total_cost, "market_value": market_value,
                    "unrealized_pl": unrealized_pl, "unrealized_pl_percentage": percentage,
                    "total_return": unrealized_pl, "total_return_percentage": percentage},
        "allocation_summary": allocation_summary,
        "positions": positions,
    }


@router.get("/portfolios")
def list_portfolios(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    service = PortfolioService(db)

    portfolios = service.list(user.id)

    return [
        {
            "id": portfolio.id,
            "name": portfolio.name,
            "broker_id": portfolio.broker_id,
            "broker_name": portfolio.broker.name if portfolio.broker else None,
            "portfolio_number_last4": portfolio.portfolio_number[-4:] if portfolio.portfolio_number else None,
            "iban_last4": portfolio.account_identifier[-4:] if portfolio.account_identifier else None,
            "cash_balance": portfolio.cash_balance,
            "base_currency_code": portfolio.base_currency.code,
        }
        for portfolio in portfolios
    ]


@router.post("/portfolios", status_code=201)
def create_portfolio(
    request: PortfolioCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    try:
        portfolio = PortfolioService(db).create(user_id=user.id, name=request.name, broker_id=request.broker_id, portfolio_number=request.portfolio_number, iban=request.iban, description=request.description, currency_code=request.currency_code)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"id": portfolio.id, "name": portfolio.name, "broker_id": portfolio.broker_id, "broker_name": portfolio.broker.name if portfolio.broker else None, "portfolio_number_last4": portfolio.portfolio_number[-4:] if portfolio.portfolio_number else None, "iban_last4": portfolio.account_identifier[-4:] if portfolio.account_identifier else None, "cash_balance": portfolio.cash_balance, "base_currency_code": portfolio.base_currency.code}


@router.post("/portfolios/{portfolio_id}/opening-balance", status_code=201)
def record_opening_portfolio_balance(portfolio_id: int, request: OpeningPortfolioRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        portfolio, positions, entry = OpeningPortfolioService(db, user.id).record(
            portfolio_id=portfolio_id,
            cash_balance=request.cash_balance,
            positions=[item.model_dump() for item in request.positions],
            as_of_date=request.as_of_date,
        )
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"portfolio_id": portfolio.id, "positions_count": len(positions), "cash_balance": portfolio.cash_balance, "journal_entry_id": entry.id}


@router.post("/portfolios/{portfolio_id}/reinvested-distributions", status_code=201)
def record_historical_reinvested_distribution(portfolio_id: int, request: ReinvestedDistributionRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    portfolio = PortfolioService(db).get(portfolio_id, user.id)
    position = db.query(Position).filter(Position.portfolio_id == portfolio.id, Position.security_id == request.security_id).first()
    security = db.query(Security).filter(Security.id == request.security_id, Security.is_active.is_(True)).first()
    if position is None or security is None:
        raise HTTPException(status_code=404, detail="The selected fund is not held in this portfolio.")
    date_key = request.transaction_date.date().isoformat()
    reference = f"{security.symbol} · reinvested-distribution:{portfolio.id}:{date_key}"
    if db.query(JournalEntry.id).filter(JournalEntry.user_id == user.id, JournalEntry.related_reference == reference).first():
        raise HTTPException(status_code=409, detail="This reinvested distribution is already recorded.")
    accounts = AccountResolver(db)
    entry = LedgerService(db).post(
        user_id=user.id,
        description=f"Reinvested distribution · {security.name}",
        transaction_date=request.transaction_date,
        lines=[
            JournalLineInput(account_id=accounts.get_by_code(3150).id, debit=request.amount),
            JournalLineInput(account_id=accounts.get_by_code(4300).id, credit=request.amount),
        ],
        related_reference=reference,
    )
    db.commit()
    return {"journal_entry_id": entry.id, "portfolio_id": portfolio.id, "security_id": security.id, "amount": request.amount, "reinvested": True}


@router.patch("/portfolios/{portfolio_id}/opening-balance")
def correct_opening_portfolio_balance(portfolio_id: int, request: OpeningPortfolioRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        portfolio, entry = OpeningPortfolioService(db, user.id).correct(portfolio_id=portfolio_id,
            cash_balance=request.cash_balance, positions=[item.model_dump() for item in request.positions], as_of_date=request.as_of_date)
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"portfolio_id": portfolio.id, "cash_balance": portfolio.cash_balance, "journal_entry_id": entry.id if entry else None}


@router.patch("/portfolios/{portfolio_id}/currency")
def update_portfolio_currency(portfolio_id: int, request: PortfolioCurrencyUpdateRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    portfolio = PortfolioService(db).get(portfolio_id, user.id)
    if portfolio.cash_balance != 0 or db.query(Trade.id).filter(Trade.portfolio_id == portfolio.id).first() is not None:
        raise HTTPException(status_code=409, detail="Settle portfolio cash and positions before changing its currency.")
    currency = db.query(Currency).filter(Currency.code == request.currency_code.upper(), Currency.is_active.is_(True)).first()
    if currency is None:
        raise HTTPException(status_code=422, detail="Select a supported portfolio currency.")
    portfolio.base_currency_id = currency.id
    db.commit()
    return {"id": portfolio.id, "base_currency_code": currency.code}


@router.patch("/portfolios/{portfolio_id}")
def update_portfolio(portfolio_id: int, request: PortfolioUpdateRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        portfolio = PortfolioService(db).update(user_id=user.id, portfolio_id=portfolio_id, name=request.name, portfolio_number=request.portfolio_number, iban=request.iban, currency_code=request.currency_code)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"id": portfolio.id, "name": portfolio.name, "broker_id": portfolio.broker_id, "broker_name": portfolio.broker.name if portfolio.broker else None, "portfolio_number_last4": portfolio.portfolio_number[-4:] if portfolio.portfolio_number else None, "iban_last4": portfolio.account_identifier[-4:] if portfolio.account_identifier else None, "cash_balance": portfolio.cash_balance, "base_currency_code": portfolio.base_currency.code}


@router.delete("/portfolios/{portfolio_id}")
def remove_portfolio(portfolio_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        portfolio = PortfolioService(db).get(portfolio_id, user.id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    has_position = db.query(Position.id).filter(Position.portfolio_id == portfolio.id, Position.quantity > 0).first() is not None
    if portfolio.cash_balance != 0 or has_position:
        raise HTTPException(status_code=409, detail="Sell all positions and transfer all portfolio cash before removing this portfolio.")
    portfolio.is_active = False
    db.commit()
    return {"id": portfolio.id, "removed": True}


@router.get("/portfolios/consolidated/summary")
def get_consolidated_portfolio_summary(db: Session = Depends(get_db), user: User = Depends(current_user)):
    result = _consolidated_summary(db, user.id)
    PortfolioHistoryService(db).record(user.id, None, result)
    return result


@router.get("/portfolios/consolidated/performance-history")
def get_consolidated_performance_history(period: str = "YTD", db: Session = Depends(get_db), user: User = Depends(current_user)):
    normalized = period if period in {"1W", "1M", "1Y", "YTD"} else "YTD"
    return PortfolioHistoryService(db).get(user.id, None, normalized)


@router.get("/portfolios/consolidated/month-end")
def get_consolidated_month_end(year: int, month: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if year < 2000 or not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="Select a valid month.")
    return PortfolioHistoryService(db).get_month_end(user.id, None, year, month)


@router.get("/portfolios/{portfolio_id}/summary")
def get_portfolio_summary(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    try:
        PortfolioService(db).get(portfolio_id, user.id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    engine = PortfolioEngine(db)
    result = engine.get_summary(
        portfolio_id=portfolio_id,
    )
    PortfolioHistoryService(db).record(user.id, portfolio_id, result)
    return result


@router.get("/portfolios/{portfolio_id}/performance-history")
def get_performance_history(portfolio_id: int, period: str = "YTD", db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        PortfolioService(db).get(portfolio_id, user.id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    normalized = period if period in {"1W", "1M", "1Y", "YTD"} else "YTD"
    return PortfolioHistoryService(db).get(user.id, portfolio_id, normalized)


@router.get("/portfolios/{portfolio_id}/month-end")
def get_portfolio_month_end(portfolio_id: int, year: int, month: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if year < 2000 or not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="Select a valid month.")
    try:
        PortfolioService(db).get(portfolio_id, user.id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return PortfolioHistoryService(db).get_month_end(user.id, portfolio_id, year, month)


@router.get(
    "/portfolios/{portfolio_id}/positions/{security_id}"
)
def get_position_detail(
    portfolio_id: int,
    security_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    try:
        PortfolioService(db).get(portfolio_id, user.id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    engine = PortfolioEngine(db)

    try:
        return engine.get_position_detail(
            portfolio_id=portfolio_id,
            security_id=security_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@router.patch("/portfolios/{portfolio_id}/positions/{security_id}")
def update_position(
    portfolio_id: int,
    security_id: int,
    request: PositionUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    try:
        PortfolioService(db).get(portfolio_id, user.id)
        position = PortfolioEngine(db).position_service.get(portfolio_id, security_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    if "fair_value" in request.model_fields_set:
        position.fair_value = request.fair_value
    if "distribution_frequency" in request.model_fields_set:
        position.distribution_frequency = request.distribution_frequency
    db.commit()
    db.refresh(position)
    return {"portfolio_id": portfolio_id, "security_id": security_id, "fair_value": position.fair_value, "distribution_frequency": position.distribution_frequency}
