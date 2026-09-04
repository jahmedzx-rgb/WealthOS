from unittest.mock import Mock

from app.accounting.services.investment_account_resolver import InvestmentAccountResolver
from app.investing.models.security import Security


def test_saudi_exchange_stock_uses_saudi_stock_ledger_account():
    resolver = InvestmentAccountResolver.__new__(InvestmentAccountResolver)
    expected = object()
    resolver.account_resolver = Mock()
    resolver.account_resolver.get_saudi_stocks_account.return_value = expected
    security = Security(symbol="7010", name="stc", security_type="STOCK", exchange="SAUDI_EXCHANGE", currency_code="SAR")

    assert resolver.resolve(security) is expected
    resolver.account_resolver.get_saudi_stocks_account.assert_called_once_with()
