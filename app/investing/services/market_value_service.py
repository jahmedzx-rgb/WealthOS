from decimal import Decimal


class MarketValueService:
    def calculate(
        self,
        quantity: Decimal,
        market_price: Decimal,
    ):
        market_value = quantity * market_price

        return {
            "quantity": quantity,
            "market_price": market_price,
            "market_value": market_value,
        }
