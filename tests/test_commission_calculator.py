from decimal import Decimal

from app.investing.services.commission_calculator import calculate_trade_commission


def test_saudi_trade_commission_includes_vat_and_rounds_to_currency():
    result = calculate_trade_commission(
        quantity=Decimal("1"),
        price=Decimal("44.74"),
        commission_rate=Decimal("0.155"),
        vat_rate=Decimal("15"),
    )
    assert result == {
        "base_commission": Decimal("0.07"),
        "vat": Decimal("0.01"),
        "total": Decimal("0.08"),
    }


def test_zero_vat_broker_keeps_base_commission():
    result = calculate_trade_commission(Decimal("100"), Decimal("25"), Decimal("0.04"), Decimal("0"))
    assert result["base_commission"] == Decimal("1.00")
    assert result["vat"] == Decimal("0.00")
    assert result["total"] == Decimal("1.00")


def test_saudi_vat_applies_only_to_broker_share_and_matches_statement_rounding():
    result = calculate_trade_commission(
        quantity=Decimal("36"),
        price=Decimal("5.64"),
        commission_rate=Decimal("0.155"),
        vat_rate=Decimal("15"),
        taxable_commission_rate=Decimal("0.105"),
    )
    assert result == {
        "base_commission": Decimal("0.31"),
        "vat": Decimal("0.03"),
        "total": Decimal("0.34"),
    }


def test_discounted_saudi_broker_keeps_market_share_outside_vat():
    total_rate = Decimal("0.120")
    market_rate = Decimal("0.050")
    result = calculate_trade_commission(
        quantity=Decimal("1000"),
        price=Decimal("10"),
        commission_rate=total_rate,
        vat_rate=Decimal("15"),
        taxable_commission_rate=total_rate - market_rate,
    )
    assert result["base_commission"] == Decimal("12.00")
    assert result["vat"] == Decimal("1.05")
    assert result["total"] == Decimal("13.05")
