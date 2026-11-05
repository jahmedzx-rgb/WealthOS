from decimal import Decimal
from types import SimpleNamespace

from app.accounting.services.wealth_analytics_service import classify_journal_entry


def account(code, account_type):
    return SimpleNamespace(code=code, account_type=account_type)


def line(debit="0", credit="0"):
    return SimpleNamespace(debit=Decimal(debit), credit=Decimal(credit))


def test_internal_account_transfer_is_never_income():
    result = classify_journal_entry("account-transfer:1:2", [
        (account(1120, "ASSET"), line(debit="500")),
        (account(1120, "ASSET"), line(credit="500")),
    ])
    assert result["kind"] == "INTERNAL_TRANSFER"
    assert result["income"] == Decimal("0.00")


def test_card_payment_and_portfolio_funding_are_excluded_transfers():
    rows = [(account(1120, "ASSET"), line(credit="700")), (account(2110, "LIABILITY"), line(debit="700"))]
    assert classify_journal_entry("credit-card-payment:4", rows)["kind"] == "INTERNAL_TRANSFER"
    assert classify_journal_entry("portfolio-funding:2:bank-account:1", rows)["income"] == Decimal("0.00")


def test_revenue_is_income_and_expense_is_spending():
    income = classify_journal_entry("deposit-return:1", [
        (account(1120, "ASSET"), line(debit="100")),
        (account(4400, "REVENUE"), line(credit="100")),
    ])
    expense = classify_journal_entry("expense:1", [
        (account(5100, "EXPENSE"), line(debit="20")),
        (account(1120, "ASSET"), line(credit="20")),
    ])
    assert income["income"] == Decimal("100")
    assert income["destination"] == "CASH_RETAINED"
    assert expense["expense"] == Decimal("20")
    assert expense["destination"] == "SPENT"
