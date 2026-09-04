from decimal import Decimal


class SaleCalculationService:
    def calculate(
        self,
        average_cost: Decimal,
        sell_quantity: Decimal,
        sell_price: Decimal,
        commission: Decimal,
    ):
        cost_basis = (
            sell_quantity * average_cost
        )

        gross_proceeds = (
            sell_quantity * sell_price
        )

        net_proceeds = (
            gross_proceeds - commission
        )

        realized_gain_loss = (
            net_proceeds - cost_basis
        )

        return {
            "cost_basis": cost_basis,
            "gross_proceeds": gross_proceeds,
            "net_proceeds": net_proceeds,
            "realized_gain_loss": realized_gain_loss,
        }
