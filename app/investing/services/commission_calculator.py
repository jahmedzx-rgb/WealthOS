from decimal import Decimal, ROUND_HALF_UP


MONEY = Decimal("0.01")


def calculate_trade_commission(
    quantity: Decimal,
    price: Decimal,
    commission_rate: Decimal,
    vat_rate: Decimal,
    taxable_commission_rate: Decimal | None = None,
) -> dict[str, Decimal]:
    gross_value = quantity * price
    base_commission = gross_value * commission_rate / Decimal("100")
    taxable_rate = commission_rate if taxable_commission_rate is None else taxable_commission_rate
    vat = gross_value * taxable_rate / Decimal("100") * vat_rate / Decimal("100")
    rounded_commission = base_commission.quantize(MONEY, rounding=ROUND_HALF_UP)
    rounded_vat = vat.quantize(MONEY, rounding=ROUND_HALF_UP)
    return {
        "base_commission": rounded_commission,
        "vat": rounded_vat,
        "total": rounded_commission + rounded_vat,
    }
