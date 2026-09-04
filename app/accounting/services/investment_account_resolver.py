from sqlalchemy.orm import Session

from app.accounting.models.account import Account
from app.accounting.services.account_resolver import AccountResolver
from app.investing.models.security import Security


class InvestmentAccountResolver:
    def __init__(self, db: Session):
        self.db = db
        self.account_resolver = AccountResolver(db)

    def resolve(
        self,
        security: Security,
    ) -> Account:
        if (
            security.security_type in {"STOCK", "REIT"}
            and security.exchange
            and security.exchange.upper() == "NASDAQ"
        ):
            return self.account_resolver.get_us_stocks_account()

        if (
            security.security_type in {"STOCK", "REIT"}
            and security.exchange
            and security.exchange.upper() in {"TADAWUL", "SAUDI_EXCHANGE"}
        ):
            return self.account_resolver.get_saudi_stocks_account()

        if security.security_type == "ETF":
            return self.account_resolver.get_etf_account()

        if security.security_type == "OPTION":
            return self.account_resolver.get_options_account()

        if security.security_type == "BOND":
            return self.account_resolver.get_bonds_account()

        if security.security_type == "MUTUAL_FUND":
            return self.account_resolver.get_mutual_funds_account()

        if security.security_type == "CRYPTO":
            return self.account_resolver.get_crypto_account()

        return self.account_resolver.get_other_investments_account()

    def get_brokerage_cash_account(self) -> Account:
        return self.account_resolver.get_brokerage_cash_account()
