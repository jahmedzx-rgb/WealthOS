from calendar import monthrange
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session

from app.investing.models.market_price import MarketPrice
from app.investing.models.portfolio import Portfolio
from app.investing.models.portfolio_valuation_snapshot import PortfolioValuationSnapshot
from app.investing.models.position import Position
from app.investing.models.security import Security
from app.investing.models.trade import Trade
from app.investing.services.exchange_rate_service import ExchangeRateService
from app.investing.services.market_price_provider import YahooMarketPriceProvider

RIYADH = timezone(timedelta(hours=3))


class PortfolioHistoryService:
    PERIOD_DAYS = {"1W": 7, "1M": 30, "1Y": 365}

    def __init__(self, db: Session):
        self.db = db
        self._historical_price_cache: dict[tuple[str, date], tuple[Decimal, datetime] | None] = {}

    def record(self, user_id: int, portfolio_id: int | None, result: dict, *, is_month_end: bool = False) -> PortfolioValuationSnapshot:
        today = datetime.now(RIYADH).date()
        summary = result.get("summary", result)
        snapshot = self.db.query(PortfolioValuationSnapshot).filter(
            PortfolioValuationSnapshot.user_id == user_id,
            PortfolioValuationSnapshot.portfolio_id == portfolio_id,
            PortfolioValuationSnapshot.valuation_date == today,
        ).first()
        if snapshot is not None and snapshot.is_month_end and not is_month_end:
            return snapshot
        if snapshot is None:
            snapshot = PortfolioValuationSnapshot(user_id=user_id, portfolio_id=portfolio_id, valuation_date=today)
            self.db.add(snapshot)
        snapshot.market_value = Decimal(str(summary["market_value"]))
        snapshot.total_cost = Decimal(str(summary["total_cost"]))
        snapshot.total_return = Decimal(str(summary["total_return"]))
        positions = result.get("positions")
        if positions is not None:
            snapshot.positions_snapshot = [self._json_safe({**item, "portfolio_id": item.get("portfolio_id", portfolio_id)}) for item in positions]
            if portfolio_id is None:
                snapshot.historical_portfolio_ids = [item.id for item in self.db.query(Portfolio).join(Portfolio.entity).filter(Portfolio.entity.has(user_id=user_id), Portfolio.created_at <= datetime.combine(today, datetime.max.time())).all()]
            else:
                snapshot.historical_portfolio_ids = [portfolio_id]
            snapshot.positions_as_of_date = today
            snapshot.positions_complete = True
        snapshot.is_month_end = is_month_end
        snapshot.recorded_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def capture_month_end(self, user_id: int, portfolio_id: int | None, snapshot_date: date) -> PortfolioValuationSnapshot:
        """Resolve prices as of the requested close and persist an immutable month-end position snapshot."""
        positions, portfolio_ids, missing = self._positions_at(user_id, portfolio_id, snapshot_date)
        snapshot = self.db.query(PortfolioValuationSnapshot).filter(
            PortfolioValuationSnapshot.user_id == user_id,
            PortfolioValuationSnapshot.portfolio_id == portfolio_id,
            PortfolioValuationSnapshot.valuation_date == snapshot_date,
        ).first()
        if snapshot is None:
            snapshot = PortfolioValuationSnapshot(
                user_id=user_id, portfolio_id=portfolio_id, valuation_date=snapshot_date,
                market_value=Decimal("0"), total_cost=Decimal("0"), total_return=Decimal("0"),
            )
            self.db.add(snapshot)
        market_value = sum((Decimal(str(item["market_value_base"])) for item in positions if item["market_value_base"] is not None), Decimal("0"))
        total_cost = sum((Decimal(str(item["total_cost_base"])) for item in positions), Decimal("0"))
        snapshot.positions_snapshot = [self._json_safe(item) for item in positions]
        snapshot.historical_portfolio_ids = portfolio_ids
        snapshot.positions_as_of_date = snapshot_date
        snapshot.positions_complete = not missing
        snapshot.is_month_end = True
        # These may be partial while a provider is unavailable. Consumers must honor positions_complete.
        snapshot.market_value = market_value
        snapshot.total_cost = total_cost
        snapshot.total_return = market_value - total_cost if not missing else Decimal("0")
        snapshot.recorded_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def get(self, user_id: int, portfolio_id: int | None, period: str) -> dict:
        today = datetime.now(UTC).date()
        if period == "YTD":
            start = date(today.year, 1, 1)
        else:
            start = today - timedelta(days=self.PERIOD_DAYS.get(period, 36500))
        snapshots = self.db.query(PortfolioValuationSnapshot).filter(
            PortfolioValuationSnapshot.user_id == user_id,
            PortfolioValuationSnapshot.portfolio_id == portfolio_id,
            PortfolioValuationSnapshot.valuation_date >= start,
        ).order_by(PortfolioValuationSnapshot.valuation_date).all()
        points = [{"date": item.valuation_date, "market_value": item.market_value, "total_cost": item.total_cost, "total_return": item.total_return} for item in snapshots]
        sufficient = len(points) >= 2
        change = Decimal("0")
        percentage = Decimal("0")
        if sufficient:
            first = Decimal(str(points[0]["market_value"]))
            last = Decimal(str(points[-1]["market_value"]))
            change = last - first
            percentage = Decimal("0") if first == 0 else (change / first) * Decimal("100")
        return {"period": period, "has_sufficient_history": sufficient, "change": change, "percentage": percentage, "points": points}

    def get_month_end(self, user_id: int, portfolio_id: int | None, year: int, month: int) -> dict:
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        snapshot = self.db.query(PortfolioValuationSnapshot).filter(
            PortfolioValuationSnapshot.user_id == user_id,
            PortfolioValuationSnapshot.portfolio_id == portfolio_id,
            PortfolioValuationSnapshot.valuation_date >= start,
            PortfolioValuationSnapshot.valuation_date <= end,
        ).order_by(PortfolioValuationSnapshot.valuation_date.desc(), PortfolioValuationSnapshot.recorded_at.desc()).first()
        if snapshot is None:
            return {"available": False, "year": year, "month": month}
        if snapshot.valuation_date != end:
            snapshot = self.db.query(PortfolioValuationSnapshot).filter(
                PortfolioValuationSnapshot.user_id == user_id,
                PortfolioValuationSnapshot.portfolio_id == portfolio_id,
                PortfolioValuationSnapshot.valuation_date == end,
            ).first()
            if snapshot is None:
                snapshot = PortfolioValuationSnapshot(
                    user_id=user_id, portfolio_id=portfolio_id, valuation_date=end,
                    market_value=Decimal("0"), total_cost=Decimal("0"), total_return=Decimal("0"),
                )
                self.db.add(snapshot)
        if snapshot.positions_snapshot is None or snapshot.positions_as_of_date != end or not snapshot.is_month_end:
            positions, historical_portfolio_ids, missing = self._positions_at(user_id, portfolio_id, end)
            snapshot.positions_snapshot = [self._json_safe(item) for item in positions]
            snapshot.historical_portfolio_ids = historical_portfolio_ids
            snapshot.positions_as_of_date = end
            snapshot.positions_complete = not missing
            snapshot.is_month_end = True
            if positions and not missing:
                market_value = sum((Decimal(str(item["market_value_base"])) for item in positions), Decimal("0"))
                total_cost = sum((Decimal(str(item["total_cost_base"])) for item in positions), Decimal("0"))
                snapshot.market_value = market_value
                snapshot.total_cost = total_cost
                snapshot.total_return = market_value - total_cost
            self.db.commit()
            self.db.refresh(snapshot)
        positions = snapshot.positions_snapshot or []
        return {"available": True, "year": year, "month": month,
                "as_of_date": snapshot.positions_as_of_date or snapshot.valuation_date,
                "valuation_snapshot_date": snapshot.valuation_date,
                "market_value": snapshot.market_value, "total_cost": snapshot.total_cost,
                "unrealized_pl": snapshot.market_value - snapshot.total_cost,
                "total_return": snapshot.total_return, "positions": positions,
                "positions_complete": snapshot.positions_complete,
                "missing_symbols": [item["symbol"] for item in positions if item.get("market_price") is None],
                "historical_portfolio_ids": snapshot.historical_portfolio_ids or []}

    def _positions_at(self, user_id: int, portfolio_id: int | None, as_of_date: date) -> tuple[list[dict], list[int], list[str]]:
        cutoff = datetime.combine(as_of_date, datetime.max.time())
        portfolios_query = self.db.query(Portfolio).join(Portfolio.entity).filter(
            Portfolio.entity.has(user_id=user_id), Portfolio.created_at <= cutoff,
        )
        if portfolio_id is not None:
            portfolios_query = portfolios_query.filter(Portfolio.id == portfolio_id)
        portfolios = portfolios_query.all()
        portfolio_ids = [item.id for item in portfolios]
        if not portfolio_ids:
            return [], [], []

        positions = self.db.query(Position, Security, Portfolio).join(Security, Position.security_id == Security.id).join(Portfolio, Position.portfolio_id == Portfolio.id).filter(Position.portfolio_id.in_(portfolio_ids)).all()
        result: list[dict] = []
        securities = {security.id: security for _, security, _ in positions}
        prices: dict[int, tuple[Decimal, datetime]] = {}
        if securities:
            stored_prices = self.db.query(MarketPrice).filter(MarketPrice.security_id.in_(securities), MarketPrice.price_date <= cutoff).order_by(MarketPrice.price_date.desc(), MarketPrice.id.desc()).all()
            for price in stored_prices:
                if price.security_id not in prices and price.price_date.date() == as_of_date:
                    prices[price.security_id] = (Decimal(price.price), price.price_date)
            unresolved = []
            for security in securities.values():
                if security.id in prices:
                    continue
                symbol = (security.market_symbol or security.symbol).strip().upper()
                cache_key = (symbol, as_of_date)
                if cache_key in self._historical_price_cache:
                    cached_price = self._historical_price_cache[cache_key]
                    if cached_price is not None:
                        prices[security.id] = cached_price
                else:
                    unresolved.append((security, symbol, cache_key))
            provider = YahooMarketPriceProvider()
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(provider.get_historical_close, symbol, as_of_date): (security.id, cache_key) for security, symbol, cache_key in unresolved}
                for future in as_completed(futures):
                    security_id, cache_key = futures[future]
                    try:
                        quote = future.result()
                        price = (quote.price, quote.price_date)
                        self._historical_price_cache[cache_key] = price
                        prices[security_id] = price
                    except Exception:
                        # Keep the position visible but unpriced; never substitute a stale quote.
                        self._historical_price_cache[cache_key] = None
                        continue
        missing: list[str] = []
        rates = ExchangeRateService()
        for position, security, portfolio in positions:
            quantity = Decimal(position.quantity)
            multiplier = Decimal("100") if security.security_type == "OPTION" else Decimal("1")
            total_cost = (quantity * Decimal(position.average_cost) * multiplier).quantize(Decimal("0.01"))
            trades = self.db.query(Trade).filter(Trade.portfolio_id == portfolio.id, Trade.security_id == security.id, Trade.trade_date > cutoff).order_by(Trade.trade_date.desc(), Trade.id.desc()).all()
            for trade in trades:
                trade_quantity = Decimal(trade.quantity)
                trade_total = trade_quantity * Decimal(trade.price) * multiplier
                commission = Decimal(trade.commission or 0)
                if trade.side == "BUY":
                    quantity -= trade_quantity
                    total_cost -= trade_total + commission
                else:
                    historical_average_cost = total_cost / quantity / multiplier if quantity else Decimal(position.average_cost)
                    quantity += trade_quantity
                    total_cost += trade_quantity * historical_average_cost * multiplier
            if quantity == 0:
                continue
            unit_cost = total_cost / quantity / multiplier
            quote = prices.get(security.id)
            market_price = quote[0] if quote else None
            market_price_date = quote[1] if quote else None
            market_value = quantity * multiplier * market_price if market_price is not None else None
            target = portfolio.base_currency.code if portfolio_id is not None else "SAR"
            cost_base = rates.convert(total_cost, security.currency_code, target)
            market_base = rates.convert(market_value, security.currency_code, target) if market_value is not None else None
            if market_price is None:
                missing.append(security.symbol)
            result.append({
                "portfolio_id": portfolio.id, "portfolio_name": portfolio.name,
                "security_id": security.id, "symbol": security.symbol, "name": security.name,
                "security_type": security.security_type, "currency_code": security.currency_code,
                "quantity": quantity, "average_cost": unit_cost, "total_cost": total_cost,
                "market_price": market_price, "market_price_date": market_price_date,
                "market_value": market_value, "unrealized_pl": market_value - total_cost if market_value is not None else None,
                "total_cost_base": cost_base, "market_value_base": market_base,
                "unrealized_pl_base": market_base - cost_base if market_base is not None else None,
            })

        return result, portfolio_ids, missing

    @classmethod
    def _json_safe(cls, value):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: cls._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._json_safe(item) for item in value]
        return value
