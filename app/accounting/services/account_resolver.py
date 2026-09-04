from sqlalchemy.orm import Session

from app.accounting.models.account import Account


class AccountResolver:
    def __init__(self, db: Session):
        self.db = db

    def get_by_code(self, code: int) -> Account:
        account = (
            self.db.query(Account)
            .filter(Account.code == code)
            .first()
        )

        if account is None:
            raise ValueError(
                f"Account with code {code} not found."
            )

        return account

    def get_by_name(self, *names: str, fallback_code: int | None = None) -> Account:
        account = self.db.query(Account).filter(Account.name.in_(names), Account.is_active.is_(True)).order_by(Account.code).first()
        if account is not None:
            return account
        if fallback_code is not None:
            return self.get_by_code(fallback_code)
        raise ValueError(f"Account not found for: {', '.join(names)}")

    def get_cash_account(self) -> Account:
        return self.get_by_name("Cash", "Cash on Hand", fallback_code=1110)

    def get_bank_account(self) -> Account:
        return self.get_by_name("Bank Accounts", "Primary Bank Account", fallback_code=1120)

    def get_brokerage_cash_account(self) -> Account:
        return self.get_by_name("Brokerage Cash", fallback_code=1130)

    def get_digital_wallet_account(self) -> Account:
        return self.get_by_code(1140)

    def get_foreign_currency_cash_account(self) -> Account:
        return self.get_by_code(1150)

    def get_time_deposit_account(self) -> Account:
        return self.get_by_code(1160)

    def get_saving_circles_account(self) -> Account:
        return self.get_by_code(1170)

    def get_us_stocks_account(self) -> Account:
        return self.get_by_code(1310)

    def get_saudi_stocks_account(self) -> Account:
        return self.get_by_code(1320)

    def get_etf_account(self) -> Account:
        return self.get_by_code(1330)

    def get_options_account(self) -> Account:
        return self.get_by_code(1340)

    def get_bonds_account(self) -> Account:
        return self.get_by_code(1350)

    def get_mutual_funds_account(self) -> Account:
        return self.get_by_code(1360)

    def get_crypto_account(self) -> Account:
        return self.get_by_code(1370)

    def get_crowdfunding_account(self) -> Account:
        return self.get_by_name("Crowdfunding Investments", fallback_code=1380)

    def get_other_investments_account(self) -> Account:
        return self.get_by_name("Other Investments", fallback_code=1390)

    def get_salary_income_account(self) -> Account:
        return self.get_by_name("Salary Income", fallback_code=4100)

    def get_rental_income_account(self) -> Account:
        return self.get_by_name("Rental Income", fallback_code=4200)

    def get_dividend_income_account(self) -> Account:
        return self.get_by_name("Dividend Income", fallback_code=4300)

    def get_interest_income_account(self) -> Account:
        return self.get_by_name("Interest Income", fallback_code=4400)

    def get_business_income_account(self) -> Account:
        return self.get_by_name("Business Income", "Other Income", fallback_code=4500)

    def get_realized_gain_account(self) -> Account:
        return self.get_by_name("Realized Gains", "Capital Gains", fallback_code=4600)

    def get_cashback_income_account(self) -> Account:
        return self.get_by_name("Cashback Income", "Other Income", fallback_code=4600)

    def get_other_income_account(self) -> Account:
        return self.get_by_name("Other Income", fallback_code=4600)

    def get_realized_loss_account(self) -> Account:
        return self.get_by_name("Realized Investment Losses", "Other Investment Expenses", fallback_code=5690)
