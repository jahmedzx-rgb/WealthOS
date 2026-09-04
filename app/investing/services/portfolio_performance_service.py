from decimal import Decimal


class PortfolioPerformanceService:
    def calculate(
        self,
        total_cost: Decimal,
        market_value: Decimal,
    ):
        total_return = (
            market_value - total_cost
        )

        total_return_percentage = (
            Decimal("0")
            if total_cost == 0
            else (
                total_return
                / total_cost
            )
        )

        return {
            "total_return": total_return,
            "total_return_percentage": (
                total_return_percentage
            ),
        }
