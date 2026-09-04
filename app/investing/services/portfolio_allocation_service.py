from decimal import Decimal


class PortfolioAllocationService:
    def calculate(
        self,
        positions: list[dict],
    ) -> list[dict]:
        total_market_value = sum(
            (
                position.get("market_value_base", position["market_value"])
                for position in positions
            ),
            Decimal("0"),
        )

        if total_market_value == Decimal("0"):
            return [
                {
                    **position,
                    "weight": Decimal("0"),
                }
                for position in positions
            ]

        return [
            {
                **position,
                "weight": (
                    position.get("market_value_base", position["market_value"])
                    / total_market_value
                ),
            }
            for position in positions
        ]
