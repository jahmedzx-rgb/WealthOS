from datetime import date, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.database.engine import get_db
from app.investing.application.buy_stock import BuyStockUseCase
from app.investing.application.sell_stock import SellStockUseCase
from app.investing.enums.trade_type import TradeType
from app.investing.schemas.buy_stock import BuyStockRequest
from app.investing.schemas.broker import BrokerCommissionRequest, BrokerRequest
from app.investing.schemas.security import MarketSecurityRequest, SaudiSecurityRequest
from app.investing.models.security import Security
from app.investing.models.position import Position
from app.investing.models.portfolio import Portfolio
from app.investing.models.broker import Broker
from app.core.models.entity import Entity
from app.investing.services.market_security_search import MarketSecurityResult, SahmkMarketSecuritySearch, YahooMarketSecuritySearch
from app.investing.services.broker_service import (
    BrokerService,
)
from app.investing.services.broker_catalog import BROKER_CATALOG, effective_commission_rate, effective_commission_source, effective_vat_rate, effective_vat_source
from app.investing.services.saudi_security_catalog import search_saudi_catalog
from app.investing.services.us_security_catalog import search_us_catalog
from app.investing.services.financial_platform_catalog import platform_catalog
from app.investing.services.market_price_provider import (
    MarketPriceProviderError,
    create_market_price_provider,
)
from app.investing.services.market_price_updater import (
    MarketPriceUpdater,
)
from app.investing.services.security_service import (
    SecurityService,
)
from app.api.v1.account import current_user
from app.core.models.user import User
from app.investing.services.portfolio_service import PortfolioService
from app.investing.services.distribution_provider import MultiSourceDistributionProvider, SahmkDistributionProvider, VerifiedSaudiExchangeDistributionProvider, YahooDistributionProvider
from app.investing.services.commission_calculator import calculate_trade_commission

router = APIRouter(
    prefix="/investing",
    tags=["Investing"],
)


@router.get("/securities/{security_id}/next-distribution")
def next_security_distribution(security_id: int, db: Session = Depends(get_db)):
    security = db.query(Security).filter(Security.id == security_id, Security.is_active.is_(True)).first()
    if security is None:
        raise HTTPException(status_code=404, detail="Security not found.")
    symbol = security.market_symbol or security.symbol
    providers = []
    if settings.SAHMK_API_KEY and security.currency_code == "SAR":
        providers.append(SahmkDistributionProvider(settings.SAHMK_API_KEY, settings.MARKET_PRICE_REQUEST_TIMEOUT_SECONDS))
    if security.currency_code == "SAR":
        providers.append(VerifiedSaudiExchangeDistributionProvider())
    providers.append(YahooDistributionProvider(settings.MARKET_PRICE_REQUEST_TIMEOUT_SECONDS))
    event, checked = MultiSourceDistributionProvider(providers).get_upcoming(symbol)
    if event is None:
        return {"available": False, "sources_checked": checked}
    return {"available": True, "distribution_date": event.distribution_date, "eligibility_date": event.eligibility_date,
            "amount_per_unit": event.amount_per_unit, "source": event.source, "date_kind": event.date_kind,
            "frequency": event.frequency, "sources_checked": checked}


@router.get("/distribution-reminders")
def distribution_reminders(days: int = 7, include_overdue: bool = False, db: Session = Depends(get_db), user: User = Depends(current_user)):
    horizon = date.today() + timedelta(days=max(0, min(days, 730)))
    rows = (db.query(Position, Security, Portfolio, Broker)
            .join(Security, Security.id == Position.security_id)
            .join(Portfolio, Portfolio.id == Position.portfolio_id)
            .outerjoin(Broker, Broker.id == Portfolio.broker_id)
            .join(Entity, Entity.id == Portfolio.entity_id)
            .filter(Entity.user_id == user.id,
                    Position.next_distribution_date.is_not(None),
                    Position.next_distribution_date >= (date.today() - timedelta(days=365) if include_overdue else date.today()),
                    Position.next_distribution_date <= horizon)
            .order_by(Position.next_distribution_date, Security.name).all())
    return [{"position_id": position.id, "security_id": security.id, "symbol": security.symbol,
             "name": security.name, "portfolio_id": portfolio.id, "portfolio_name": portfolio.name,
             "distribution_date": position.next_distribution_date,
             "expected_amount": position.expected_distribution_amount,
             "frequency": position.distribution_frequency,
             "withholding_tax_rate": broker.dividend_withholding_tax_rate if broker and broker.dividend_withholding_tax_rate is not None else user.default_dividend_withholding_tax_rate,
             "expected_tax_amount": (position.expected_distribution_amount * (broker.dividend_withholding_tax_rate if broker and broker.dividend_withholding_tax_rate is not None else user.default_dividend_withholding_tax_rate) / 100) if position.expected_distribution_amount is not None else None,
             "expected_net_amount": (position.expected_distribution_amount * (1 - (broker.dividend_withholding_tax_rate if broker and broker.dividend_withholding_tax_rate is not None else user.default_dividend_withholding_tax_rate) / 100)) if position.expected_distribution_amount is not None else None,
             "currency_code": security.currency_code,
             "days_until": (position.next_distribution_date - date.today()).days}
            for position, security, portfolio, broker in rows]


@router.get("/brokers")
def list_brokers(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    service = BrokerService(db, user.id)

    brokers = service.list()

    return [
        {
            "id": broker.id,
            "code": broker.code,
            "name": broker.name,
            "country": broker.country,
            "website": broker.website,
            "institution_name": broker.institution_name or broker.name,
            "execution_partner": broker.execution_partner,
            "commission_rate": broker.commission_rate,
            "commission_source": broker.commission_source,
            "commission_tax_rate": broker.commission_tax_rate,
            "commission_tax_source": broker.commission_tax_source,
            "dividend_withholding_tax_rate": broker.dividend_withholding_tax_rate,
            "dividend_withholding_tax_source": broker.dividend_withholding_tax_source,
        }
        for broker in brokers
    ]


@router.get("/securities")
def list_securities(
    db: Session = Depends(get_db),
):
    service = SecurityService(db)

    securities = service.list()

    return [
        {
            "id": security.id,
            "symbol": security.symbol,
            "name": security.name,
            "exchange": security.exchange,
            "currency_code": security.currency_code,
            "market_symbol": security.market_symbol,
        }
        for security in securities
    ]


@router.get("/brokers/catalog")
def broker_catalog():
    return [{"name": item.name, "country": item.country, "website": item.website, "aliases": item.aliases, "default_commission_rate": effective_commission_rate(item), "commission_source": effective_commission_source(item), "default_commission_tax_rate": effective_vat_rate(item), "commission_tax_source": effective_vat_source(item), "institution_name": item.institution_name or item.name, "execution_partner": item.execution_partner} for item in BROKER_CATALOG]


@router.post("/brokers", status_code=201)
def create_broker(
    request: BrokerRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    try:
        broker = BrokerService(db, user.id).create(
            name=request.name,
            country=request.country,
            website=request.website,
            commission_rate=request.commission_rate,
            commission_tax_rate=request.commission_tax_rate,
            dividend_withholding_tax_rate=request.dividend_withholding_tax_rate,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    return {
        "id": broker.id,
        "code": broker.code,
        "name": broker.name,
        "country": broker.country,
        "website": broker.website,
        "institution_name": broker.institution_name or broker.name,
        "execution_partner": broker.execution_partner,
        "commission_rate": broker.commission_rate,
        "commission_source": broker.commission_source,
        "commission_tax_rate": broker.commission_tax_rate,
        "commission_tax_source": broker.commission_tax_source,
        "dividend_withholding_tax_rate": broker.dividend_withholding_tax_rate,
        "dividend_withholding_tax_source": broker.dividend_withholding_tax_source,
    }


@router.patch("/brokers/{broker_id}/commission")
def update_broker_commission(broker_id: int, request: BrokerCommissionRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        broker = BrokerService(db, user.id).get(broker_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    broker.commission_rate = request.commission_rate
    broker.commission_source = "User supplied"
    broker.commission_tax_rate = request.commission_tax_rate
    broker.commission_tax_source = "User supplied"
    broker.dividend_withholding_tax_rate = request.dividend_withholding_tax_rate
    broker.dividend_withholding_tax_source = "Broker override" if request.dividend_withholding_tax_rate is not None else "Investor profile default"
    if "website" in request.model_fields_set:
        broker.website = request.website
    db.commit()
    return {"id": broker.id, "website": broker.website, "commission_rate": broker.commission_rate, "commission_source": broker.commission_source, "commission_tax_rate": broker.commission_tax_rate, "commission_tax_source": broker.commission_tax_source, "dividend_withholding_tax_rate": broker.dividend_withholding_tax_rate, "dividend_withholding_tax_source": broker.dividend_withholding_tax_source}


@router.delete("/brokers/{broker_id}")
def close_broker(broker_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return BrokerService(db, user.id).close(broker_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/securities/saudi", status_code=201)
def create_saudi_security(
    request: SaudiSecurityRequest,
    db: Session = Depends(get_db),
):
    existing = db.query(Security).filter(Security.symbol == request.symbol).first()
    if existing is not None:
        if existing.exchange != "SAUDI_EXCHANGE":
            raise HTTPException(status_code=409, detail="This symbol is already used by another market.")
        return {
            "id": existing.id,
            "symbol": existing.symbol,
            "name": existing.name,
            "exchange": existing.exchange,
            "currency_code": existing.currency_code,
            "market_symbol": existing.market_symbol,
        }

    security = Security(
        symbol=request.symbol,
        market_symbol=f"{request.symbol}.SR",
        name=request.name,
        security_type=request.security_type,
        exchange="SAUDI_EXCHANGE",
        currency_code="SAR",
    )
    db.add(security)
    db.commit()
    db.refresh(security)
    return {
        "id": security.id,
        "symbol": security.symbol,
        "name": security.name,
        "exchange": security.exchange,
        "currency_code": security.currency_code,
        "market_symbol": security.market_symbol,
    }


def security_dict(security: Security):
    catalog_item = next((item for item in search_saudi_catalog(security.symbol) if item.symbol == security.symbol), None) if security.exchange == "SAUDI_EXCHANGE" or str(security.market_symbol or "").endswith(".SR") else None
    return {"id": security.id, "symbol": security.symbol, "name": security.name, "name_ar": catalog_item.name_ar if catalog_item else None, "name_en": catalog_item.name_en if catalog_item else security.name, "exchange": security.exchange, "currency_code": security.currency_code, "market_symbol": security.market_symbol, "security_type": security.security_type}


@router.get("/financial-platforms")
def financial_platforms():
    return platform_catalog()


@router.get("/securities/search")
def search_securities(query: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    normalized = query.strip().lstrip("$").strip()
    global_aliases = {
        "تسلا": "TSLA", "tesla": "TSLA",
        "ابل": "AAPL", "أبل": "AAPL", "آبل": "AAPL", "apple": "AAPL",
    }
    normalized = global_aliases.get(normalized.lower(), normalized)
    if len(normalized) < 2:
        return []
    pattern = f"%{normalized}%"
    local = db.query(Security).filter((Security.symbol.ilike(pattern)) | (Security.name.ilike(pattern))).limit(8).all()
    results = [{**security_dict(item), "registered": True} for item in local]
    known = {item["market_symbol"] or item["symbol"] for item in results}
    catalog_rows = [{"id": None, "symbol": item.symbol, "market_symbol": item.market_symbol, "name": item.name, "name_ar": item.name_ar, "name_en": item.name_en, "security_type": item.security_type, "exchange": "SAUDI_EXCHANGE", "currency_code": "SAR", "registered": False} for item in search_saudi_catalog(normalized)[:10]]
    catalog_rows.extend({"id": None, **item.__dict__, "name_ar": None, "name_en": item.name, "registered": False} for item in search_us_catalog(normalized))
    market_symbols = [item["market_symbol"] for item in catalog_rows if item["market_symbol"] not in known]
    existing_catalog = {item.market_symbol: item for item in db.query(Security).filter(Security.market_symbol.in_(market_symbols)).all()} if market_symbols else {}
    for item in catalog_rows:
        market_symbol = item["market_symbol"]
        if market_symbol in known:
            continue
        existing = existing_catalog.get(market_symbol)
        results.append({**security_dict(existing), "registered": True} if existing else item)
        known.add(market_symbol)
    if not results and settings.SAHMK_API_KEY:
        try:
            saudi_remote = SahmkMarketSecuritySearch(settings.SAHMK_API_KEY, settings.MARKET_PRICE_REQUEST_TIMEOUT_SECONDS).search(normalized)
        except MarketPriceProviderError:
            saudi_remote = []
        for item in saudi_remote:
            if item.market_symbol in known:
                continue
            existing = db.query(Security).filter(Security.market_symbol == item.market_symbol).first()
            results.append({**security_dict(existing), "registered": True} if existing else {"id": None, **item.__dict__, "registered": False})
            known.add(item.market_symbol)
    remote = []
    if not results:
        try:
            remote = YahooMarketSecuritySearch(settings.MARKET_PRICE_REQUEST_TIMEOUT_SECONDS).search(normalized)
        except MarketPriceProviderError:
            remote = []
    for item in remote:
        if item.market_symbol in known:
            continue
        results.append({"id": None, **item.__dict__, "registered": False})
        known.add(item.market_symbol)
    owned_security_ids = {
        security_id for (security_id,) in (
            db.query(Position.security_id)
            .join(Portfolio, Position.portfolio_id == Portfolio.id)
            .join(Broker, Portfolio.broker_id == Broker.id)
            .filter(Broker.user_id == user.id, Portfolio.is_active.is_(True), Position.quantity > 0)
            .distinct()
            .all()
        )
    }
    for result in results:
        result["owned"] = result.get("id") in owned_security_ids
    return results[:10]


@router.post("/securities/register", status_code=201)
def register_market_security(request: MarketSecurityRequest, db: Session = Depends(get_db)):
    existing = db.query(Security).filter((Security.market_symbol == request.market_symbol) | (Security.symbol == request.symbol)).first()
    if existing is not None:
        return security_dict(existing)
    verified = None
    if request.market_symbol.upper().endswith(".SR"):
        catalog_item = next((item for item in search_saudi_catalog(request.symbol) if item.market_symbol == request.market_symbol.upper()), None)
        if catalog_item is not None:
            verified = MarketSecurityResult(symbol=catalog_item.symbol, market_symbol=catalog_item.market_symbol, name=catalog_item.name, security_type=catalog_item.security_type, exchange="SAUDI_EXCHANGE", currency_code="SAR")
    else:
        catalog_item = next((item for item in search_us_catalog(request.symbol) if item.market_symbol == request.market_symbol.upper()), None)
        if catalog_item is not None:
            verified = catalog_item
    if verified is None and request.market_symbol.upper().endswith(".SR") and settings.SAHMK_API_KEY:
        try:
            verified = SahmkMarketSecuritySearch(settings.SAHMK_API_KEY, settings.MARKET_PRICE_REQUEST_TIMEOUT_SECONDS).resolve(request.market_symbol)
        except MarketPriceProviderError:
            verified = None
    if verified is None:
        try:
            verified = YahooMarketSecuritySearch(settings.MARKET_PRICE_REQUEST_TIMEOUT_SECONDS).resolve(request.market_symbol)
        except MarketPriceProviderError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
    if not verified.currency_code:
        raise HTTPException(status_code=422, detail="The market currency could not be verified.")
    security_data = verified.__dict__.copy()
    if request.security_type == "REIT":
        security_data["security_type"] = "REIT"
    security = Security(**security_data)
    db.add(security)
    db.commit()
    db.refresh(security)
    return security_dict(security)


@router.post("/market-prices/update")
def update_market_prices(
    security_id: int | None = None,
    db: Session = Depends(get_db),
):
    try:
        provider = create_market_price_provider(
            provider_name=settings.MARKET_PRICE_PROVIDER,
            fallback_provider_name=(settings.MARKET_PRICE_FALLBACK_PROVIDER or ("alpha_vantage" if settings.ALPHA_VANTAGE_API_KEY else None)),
            alpha_vantage_api_key=(
                settings.ALPHA_VANTAGE_API_KEY
            ),
            timeout_seconds=(
                settings.MARKET_PRICE_REQUEST_TIMEOUT_SECONDS
            ),
            request_interval_seconds=(
                settings.MARKET_PRICE_REQUEST_INTERVAL_SECONDS
            ),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    updater = MarketPriceUpdater(db, provider)

    try:
        if security_id is None:
            market_prices = updater.update_all()
        else:
            market_prices = [
                updater.update_security(security_id)
            ]
    except MarketPriceProviderError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    return {
        "updated_count": len(market_prices),
        "market_prices": [
            {
                "security_id": market_price.security_id,
                "price": market_price.price,
                "price_date": market_price.price_date,
            }
            for market_price in market_prices
        ],
    }


@router.post("/trades")
def create_trade(
    request: BuyStockRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    try:
        portfolio = PortfolioService(db).get(request.portfolio_id, user.id)
        broker = BrokerService(db, user.id).get(request.broker_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    if portfolio.broker_id is not None and portfolio.broker_id != request.broker_id:
        raise HTTPException(status_code=422, detail="The selected portfolio belongs to a different broker.")
    if broker.commission_rate is None or broker.commission_tax_rate is None:
        raise HTTPException(status_code=422, detail="Complete the broker commission and VAT settings before trading.")
    security = db.query(Security).filter(Security.id == request.security_id, Security.is_active.is_(True)).first()
    if security is None:
        raise HTTPException(status_code=404, detail="Security not found.")
    # Saudi local-trading commission contains a fixed 0.05% CMA/Exchange share.
    # VAT is applied to the broker's remaining share, not to the whole 0.155%.
    taxable_commission_rate = max(broker.commission_rate - Decimal("0.05"), Decimal("0")) if security.currency_code == "SAR" else None
    calculated_commission = calculate_trade_commission(
        request.quantity, request.price, broker.commission_rate, broker.commission_tax_rate,
        taxable_commission_rate=taxable_commission_rate,
    )["total"]
    if request.side == TradeType.BUY:
        try:
            result = BuyStockUseCase(db, user.id).execute(
                portfolio_id=request.portfolio_id,
                broker_id=request.broker_id,
                security_id=request.security_id,
                quantity=request.quantity,
                price=request.price,
                commission=calculated_commission,
                trade_date=request.trade_date,
            )
        except ValueError as error:
            db.rollback()
            raise HTTPException(status_code=422, detail=str(error)) from error
        position = result["position"]
        if request.next_distribution_date is not None or request.distribution_frequency is not None or request.fair_value is not None:
            position.next_distribution_date = request.next_distribution_date
            position.expected_distribution_amount = request.expected_distribution_amount
            position.distribution_frequency = request.distribution_frequency
            if request.fair_value is not None:
                position.fair_value = request.fair_value
            db.commit()
            db.refresh(position)
        return result

    if request.side == TradeType.SELL:
        try:
            return SellStockUseCase(db, user.id).execute(
                portfolio_id=request.portfolio_id,
                broker_id=request.broker_id,
                security_id=request.security_id,
                quantity=request.quantity,
                price=request.price,
                commission=calculated_commission,
                trade_date=request.trade_date,
            )
        except ValueError as error:
            db.rollback()
            raise HTTPException(status_code=422, detail=str(error)) from error

    raise ValueError(
        f"Unsupported trade type: {request.side}"
    )
