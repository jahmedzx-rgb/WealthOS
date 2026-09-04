from decimal import Decimal


class PortfolioValuationService:
    def calculate(
        self,
        total_cost: Decimal,
        market_value: Decimal,
    ):
        unrealized_pl = (
            market_value - total_cost
        )

        return {
            "total_cost": total_cost,
            "market_value": market_value,
            "unrealized_pl": unrealized_pl,
        }
