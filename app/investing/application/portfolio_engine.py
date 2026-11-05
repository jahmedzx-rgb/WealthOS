from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.investing.models.market_price import MarketPrice
from app.investing.models.security import Security

from app.investing.services.market_price_service import (
    MarketPriceService,
)
from app.investing.services.market_value_service import (
    MarketValueService,
)
from app.investing.services.portfolio_allocation_service import (
    PortfolioAllocationService,
)
from app.investing.services.portfolio_performance_service import (
    PortfolioPerformanceService,
)
from app.investing.services.portfolio_service import (
    PortfolioService,
)
from app.investing.services.portfolio_valuation_service import (
    PortfolioValuationService,
)
from app.investing.services.position_service import (
    PositionService,
)
from app.investing.services.security_service import (
    SecurityService,
)
from app.investing.services.trade_service import (
    TradeService,
)
from app.investing.services.exchange_rate_service import ExchangeRateService
from app.investing.services.saudi_security_catalog import SAUDI_SECURITY_CATALOG

_SAUDI_SECURITY_BY_SYMBOL = {item.symbol: item for item in SAUDI_SECURITY_CATALOG}


class PortfolioEngine:
    def __init__(self, db: Session):
        self.db = db
        self.portfolio_service = PortfolioService(db)
        self.position_service = PositionService(db)
        self.security_service = SecurityService(db)
        self.trade_service = TradeService(db)
        self.market_price_service = MarketPriceService(db)
        self.market_value_service = MarketValueService()
        self.portfolio_allocation_service = (
            PortfolioAllocationService()
        )
        self.portfolio_performance_service = (
            PortfolioPerformanceService()
        )
        self.portfolio_valuation_service = (
            PortfolioValuationService()
        )
        self.exchange_rate_service = ExchangeRateService()

    def get_summary(
        self,
        portfolio_id: int,
    ):
        portfolio = self.portfolio_service.get(
            portfolio_id
        )

        positions = (
            self.position_service.list_by_portfolio(
                portfolio_id
            )
        )

        position_items = self._build_positions(
            positions,
            portfolio.base_currency.code,
        )

        allocated_positions = (
            self.portfolio_allocation_service.calculate(
                position_items
            )
        )

        totals = self._calculate_totals(
            allocated_positions
        )

        allocation_summary = (
            self._build_allocation_summary(
                allocated_positions
            )
        )

        return {
            "portfolio": {
                "id": portfolio.id,
                "code": portfolio.code,
                "name": portfolio.name,
                "base_currency_id": portfolio.base_currency_id,
                "base_currency_code": portfolio.base_currency.code,
                "cash_balance": portfolio.cash_balance,
            },
            "summary": {
                "positions_count": len(
                    allocated_positions
                ),
                **totals,
            },
            "allocation_summary": allocation_summary,
            "positions": allocated_positions,
        }

    def get_position_detail(
        self,
        portfolio_id: int,
        security_id: int,
    ):
        position = self.position_service.position_repository.get(
            portfolio_id,
            security_id,
        )

        if position is None:
            raise ValueError("Position not found.")

        position_item = self._build_position_item(
            position
        )

        trades = self.trade_service.list_by_position(
            portfolio_id=portfolio_id,
            security_id=security_id,
        )

        position_item["trade_history"] = [
            {
                "id": trade.id,
                "broker_id": trade.broker_id,
                "side": trade.side,
                "quantity": trade.quantity,
                "price": trade.price,
                "commission": trade.commission,
                "trade_date": trade.trade_date,
            }
            for trade in trades
        ]

        return position_item

    def _build_positions(
        self,
        positions,
        base_currency_code: str,
    ):
        security_ids = {position.security_id for position in positions}
        if not security_ids:
            return []

        securities = {
            security.id: security
            for security in self.db.query(Security).filter(Security.id.in_(security_ids)).all()
        }
        ranked_prices = (
            self.db.query(
                MarketPrice.id.label("market_price_id"),
                func.row_number().over(
                    partition_by=MarketPrice.security_id,
                    order_by=(MarketPrice.price_date.desc(), MarketPrice.id.desc()),
                ).label("price_rank"),
            )
            .filter(MarketPrice.security_id.in_(security_ids))
            .subquery()
        )
        latest_prices = {
            market_price.security_id: market_price
            for market_price in self.db.query(MarketPrice)
            .join(ranked_prices, ranked_prices.c.market_price_id == MarketPrice.id)
            .filter(ranked_prices.c.price_rank == 1)
            .all()
        }
        items = [
            self._build_position_item(
                position,
                base_currency_code,
                security=securities.get(position.security_id),
                latest_price=latest_prices.get(position.security_id),
            )
            for position in positions
        ]
        shares_by_symbol = {
            item["symbol"].upper(): Decimal(str(item["quantity"]))
            for item in items
            if item["security_type"] != "OPTION" and Decimal(str(item["quantity"])) > 0
        }
        for item in items:
            item["allocation_type"] = self._option_allocation_type(item, shares_by_symbol)
        return items

    @staticmethod
    def _option_allocation_type(item: dict, shares_by_symbol: dict[str, Decimal]) -> str:
        if item["security_type"] != "OPTION" or Decimal(str(item["quantity"])) >= 0:
            return item["security_type"]
        symbol = item["symbol"].upper()
        name = item["name"].upper()
        underlying = symbol.split("-", 1)[0]
        if underlying not in shares_by_symbol:
            # Some brokers export OCC-style option symbols without a separator
            # (for example ZETA20261218C35). Match the known underlying root.
            def matches_option_root(candidate: str) -> bool:
                suffix = symbol[len(candidate):]
                return symbol.startswith(candidate) and any(
                    suffix[expiry_length:expiry_length + 1] in {"C", "P"}
                    and suffix[:expiry_length].isdigit()
                    for expiry_length in (8, 6)
                )

            underlying = next((
                candidate for candidate in sorted(shares_by_symbol, key=len, reverse=True)
                if matches_option_root(candidate)
            ), underlying)
        contracts = abs(Decimal(str(item["quantity"])))
        is_call = " CALL" in f" {name}" or "-C" in symbol
        is_put = " PUT" in f" {name}" or "-P" in symbol
        if is_call and shares_by_symbol.get(underlying, Decimal("0")) >= contracts * Decimal("100"):
            return "COVERED_CALL"
        if is_put:
            return "CASH_SECURED_PUT"
        return "OPTION"

    def _build_position_item(
        self,
        position,
        base_currency_code: str | None = None,
        *,
        security=None,
        latest_price=None,
    ):
        if security is None:
            security = self.security_service.get(position.security_id)

        if latest_price is None:
            latest_price = self.market_price_service.get_latest(position.security_id)

        multiplier = Decimal("100") if security.security_type == "OPTION" else Decimal("1")

        total_cost = (
            position.quantity
            * position.average_cost
            * multiplier
        ).quantize(Decimal("0.01"))

        market = self.market_value_service.calculate(
            quantity=position.quantity * multiplier,
            market_price=latest_price.price,
        )
        target_currency = base_currency_code or security.currency_code
        catalog_item = _SAUDI_SECURITY_BY_SYMBOL.get(security.symbol)
        total_cost_base = self.exchange_rate_service.convert(total_cost, security.currency_code, target_currency)
        market_value_base = self.exchange_rate_service.convert(market["market_value"], security.currency_code, target_currency)

        return {
            "security_id": security.id,
            "symbol": security.symbol,
            "name": security.name,
            "name_ar": catalog_item.name_ar if catalog_item else None,
            "name_en": catalog_item.name_en if catalog_item else security.name,
            "security_type": security.security_type,
            "allocation_type": security.security_type,
            "exchange": security.exchange,
            "currency_code": security.currency_code,
            "quantity": position.quantity,
            "next_distribution_date": position.next_distribution_date,
            "expected_distribution_amount": position.expected_distribution_amount,
            "distribution_frequency": position.distribution_frequency,
            "fair_value": position.fair_value,
            "average_cost": position.average_cost,
            "total_cost": total_cost,
            "market_price": market["market_price"],
            "market_price_date": latest_price.price_date,
            "market_value": market["market_value"],
            "total_cost_base": total_cost_base,
            "market_value_base": market_value_base,
            "unrealized_pl_base": market_value_base - total_cost_base,
            "unrealized_pl": (
                market["market_value"]
                - total_cost
            ),
        }

    def _build_allocation_summary(
        self,
        position_items,
    ):
        allocation_summary = {}

        for item in position_items:
            security_type = item.get("allocation_type", item["security_type"])

            allocation_summary[security_type] = (
                allocation_summary.get(
                    security_type,
                    Decimal("0"),
                )
                + item["weight"]
            )

        return allocation_summary

    def _calculate_totals(
        self,
        position_items,
    ):
        total_cost = sum(
            (
                item.get("total_cost_base", item["total_cost"])
                for item in position_items
            ),
            Decimal("0"),
        )

        market_value = sum(
            (
                item.get("market_value_base", item["market_value"])
                for item in position_items
            ),
            Decimal("0"),
        )

        valuation = (
            self.portfolio_valuation_service.calculate(
                total_cost=total_cost,
                market_value=market_value,
            )
        )

        performance = (
            self.portfolio_performance_service.calculate(
                total_cost=total_cost,
                market_value=market_value,
            )
        )

        return {
            **valuation,
            **performance,
        }
