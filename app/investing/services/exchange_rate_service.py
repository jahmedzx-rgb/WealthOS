from decimal import Decimal


class ExchangeRateService:
    """Indicative beta rates expressed as SAR per currency unit."""

    SAR_RATES = {
        "SAR": Decimal("1"),
        "USD": Decimal("3.75"),
        "EUR": Decimal("4.08"),
        "GBP": Decimal("4.76"),
        "JPY": Decimal("0.025"),
        "AED": Decimal("1.021"),
        "KWD": Decimal("12.22"),
    }

    def convert(self, amount: Decimal, source: str, target: str) -> Decimal:
        try:
            return amount * self.SAR_RATES[source] / self.SAR_RATES[target]
        except KeyError as error:
            raise ValueError(f"Unsupported currency conversion: {source} to {target}.") from error
