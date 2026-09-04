import pytest
from pydantic import ValidationError

from app.investing.schemas.security import SaudiSecurityRequest


def test_saudi_security_normalizes_valid_symbol_and_name():
    request = SaudiSecurityRequest(symbol="1120", name="  Al Rajhi Bank  ")
    assert request.symbol == "1120"
    assert request.name == "Al Rajhi Bank"
    assert request.security_type == "STOCK"


@pytest.mark.parametrize("symbol", ["112", "11200", "ABCD"])
def test_saudi_security_rejects_invalid_symbol(symbol):
    with pytest.raises(ValidationError):
        SaudiSecurityRequest(symbol=symbol, name="Invalid")
