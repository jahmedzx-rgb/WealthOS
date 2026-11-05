from datetime import date
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func

import app.database.model_registry  # noqa: F401
from app.accounting.models.account import Account
from app.accounting.models.bank_account import BankAccount
from app.accounting.models.credit_card_account import CreditCardAccount
from app.accounting.models.deposit import Deposit
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.models.loan import Loan
from app.accounting.models.property_asset import PropertyAsset
from app.accounting.services.financial_summary_service import FinancialSummaryService
from app.accounting.services.reporting_service import ReportingService
from app.core.models.user import User
from app.core.models.entity import Entity
from app.database.engine import SessionLocal
from app.investing.models.portfolio import Portfolio
from app.investing.models.position import Position


def money(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))


failed = False
with SessionLocal() as db:
    users = db.query(User).order_by(User.id).all()
    for user in users:
        summary = FinancialSummaryService(db, user.id).get()
        report = ReportingService(db, user.id).get("balance_sheet", date(1900, 1, 1), date.today())
        report_values = {row["label"]: money(row["value"]) for row in report["rows"] if row["is_total"]}
        banks = money(
            db.query(func.coalesce(func.sum(BankAccount.current_balance), 0))
            .filter(BankAccount.user_id == user.id, BankAccount.account_type != "DIGITAL_WALLET")
            .scalar()
        )
        cards = money(db.query(func.coalesce(func.sum(CreditCardAccount.current_balance), 0)).filter(CreditCardAccount.user_id == user.id, CreditCardAccount.is_active.is_(True)).scalar())
        deposits = money(db.query(func.coalesce(func.sum(Deposit.current_balance), 0)).filter(Deposit.user_id == user.id, Deposit.status.in_(["ACTIVE", "MATURED"])).scalar())
        loans = money(db.query(func.coalesce(func.sum(Loan.outstanding_balance), 0)).filter(Loan.user_id == user.id, Loan.status == "ACTIVE").scalar())
        wallets = money(db.query(func.coalesce(func.sum(BankAccount.current_balance), 0)).filter(BankAccount.user_id == user.id, BankAccount.account_type == "DIGITAL_WALLET").scalar())
        portfolio_cash = money(db.query(func.coalesce(func.sum(Portfolio.cash_balance), 0)).join(Entity, Portfolio.entity_id == Entity.id).filter(Entity.user_id == user.id, Portfolio.is_active.is_(True)).scalar())
        position_cost = money(db.query(func.coalesce(func.sum(Position.quantity * Position.average_cost), 0)).join(Portfolio, Position.portfolio_id == Portfolio.id).join(Entity, Portfolio.entity_id == Entity.id).filter(Entity.user_id == user.id, Portfolio.is_active.is_(True), Position.quantity > 0).scalar())
        properties = money(db.query(func.coalesce(func.sum(PropertyAsset.current_value), 0)).filter(PropertyAsset.user_id == user.id, PropertyAsset.status == "ACTIVE").scalar())
        def ledger_asset(*codes: int):
            return money(db.query(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0)).join(JournalEntry).join(Account).filter(JournalEntry.user_id == user.id, Account.code.in_(codes)).scalar())
        def ledger_liability(*codes: int):
            return money(db.query(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), 0)).join(JournalEntry).join(Account).filter(JournalEntry.user_id == user.id, Account.code.in_(codes)).scalar())
        ledger_banks = ledger_asset(1120)
        ledger_wallets = ledger_asset(1175)
        ledger_portfolio_cash = ledger_asset(1130)
        ledger_position_cost = ledger_asset(1310, 1320, 1330, 1340, 1350, 1360, 1370, 1380, 1390)
        ledger_properties = ledger_asset(1210)
        ledger_cards = ledger_liability(2110)
        ledger_deposit = money(db.query(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0)).join(JournalEntry).join(Account).filter(JournalEntry.user_id == user.id, Account.code == 1160).scalar())
        ledger_loans = money(db.query(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), 0)).join(JournalEntry).join(Account).filter(JournalEntry.user_id == user.id, Account.code.in_([2140, 2210, 2220])).scalar())
        unbalanced = db.query(JournalEntry.id).join(JournalLine).filter(JournalEntry.user_id == user.id).group_by(JournalEntry.id).having(func.abs(func.sum(JournalLine.debit - JournalLine.credit)) > Decimal("0.005")).count()
        checks = {
            "balance_sheet_assets": money(summary["total_assets"]) == report_values.get("Total Assets"),
            "balance_sheet_liabilities": money(summary["total_liabilities"]) == report_values.get("Total Liabilities"),
            "balance_sheet_net_worth": money(summary["net_worth"]) == report_values.get("Net Worth"),
            "bank_balances": money(summary["bank_account_summary"]["total_balance"]) == banks,
            "bank_subledger": banks == ledger_banks,
            "digital_wallet_subledger": wallets == ledger_wallets,
            "portfolio_cash_subledger": portfolio_cash == ledger_portfolio_cash,
            "position_cost_subledger": position_cost == ledger_position_cost,
            "property_subledger": properties == ledger_properties,
            "credit_card_used": money(summary["credit_card_summary"]["used"]) == cards,
            "credit_card_subledger": cards == ledger_cards,
            "deposit_subledger": deposits == ledger_deposit,
            "loan_subledger": loans == ledger_loans,
            "all_journal_entries_balanced": unbalanced == 0,
        }
        failed = failed or not all(checks.values())
        print({
            "user_id": user.id,
            "checks": checks,
            "values": {
                "assets": str(money(summary["total_assets"])),
                "liabilities": str(money(summary["total_liabilities"])),
                "net_worth": str(money(summary["net_worth"])),
                "banks": str(banks),
                "banks_ledger": str(ledger_banks),
                "wallets": str(wallets),
                "wallets_ledger": str(ledger_wallets),
                "portfolio_cash": str(portfolio_cash),
                "portfolio_cash_ledger": str(ledger_portfolio_cash),
                "position_cost": str(position_cost),
                "position_cost_ledger": str(ledger_position_cost),
                "properties": str(properties),
                "properties_ledger": str(ledger_properties),
                "cards": str(cards),
                "cards_ledger": str(ledger_cards),
                "deposits_operational": str(deposits),
                "deposits_ledger": str(ledger_deposit),
                "loans_operational": str(loans),
                "loans_ledger": str(ledger_loans),
                "unbalanced_entries": unbalanced,
            },
        })

if failed:
    raise SystemExit("Dashboard/accounting reconciliation failed.")
