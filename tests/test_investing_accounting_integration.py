from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.accounting.models import Account, JournalEntry, JournalLine
from app.core.models.currency import Currency
from app.core.models.entity import Entity
from app.core.models.user import User
from app.database.base import Base
from app.investing.application.buy_stock_service import BuyStockService
from app.investing.application.portfolio_engine import PortfolioEngine
from app.investing.application.sell_stock_service import SellStockService
from app.investing.models.broker import Broker
from app.investing.models.portfolio import Portfolio
from app.investing.models.portfolio_objective import PortfolioObjective
from app.investing.models.portfolio_strategy import PortfolioStrategy
from app.investing.models.security import Security
from app.investing.services.opening_portfolio_service import OpeningPortfolioService
from app.accounting.services.financial_summary_service import FinancialSummaryService


def test_saudi_reit_buy_and_profitable_sale_are_fully_linked_to_accounting():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id=1, email="audit@example.com", full_name="Audit User")
    currency = Currency(code="SAR", name="Saudi Riyal", symbol="SAR")
    db.add_all([user, currency]); db.flush()
    entity = Entity(user_id=1, code="PERSONAL", name="Personal", entity_type="PERSONAL", base_currency_id=currency.id)
    strategy = PortfolioStrategy(code="BALANCED", name="Balanced")
    objective = PortfolioObjective(code="GROWTH", name="Growth")
    broker = Broker(user_id=1, code="SNB", name="SNB Capital")
    db.add_all([entity, strategy, objective, broker]); db.flush()
    portfolio = Portfolio(code="SAUDI", name="Saudi Stocks", entity_id=entity.id, broker_id=broker.id, strategy_id=strategy.id, objective_id=objective.id, base_currency_id=currency.id, cash_balance=Decimal("1000"))
    security = Security(symbol="4348", name="Alkhabeer REIT Fund", security_type="REIT", exchange="SAUDI_EXCHANGE", currency_code="SAR")
    accounts = [
        Account(code=1130, name="Brokerage Cash", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=1320, name="Saudi Stocks", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=4600, name="Capital Gains", account_type="REVENUE", normal_balance="CREDIT"),
        Account(code=5610, name="Brokerage Fees", account_type="EXPENSE", normal_balance="DEBIT"),
        Account(code=5690, name="Other Investment Expenses", account_type="EXPENSE", normal_balance="DEBIT"),
    ]
    db.add_all([portfolio, security, *accounts]); db.commit()
    trade_date = datetime(2026, 8, 20, 12, 30)

    bought = BuyStockService(db, 1).buy(portfolio.id, broker.id, security.id, Decimal("10"), Decimal("5"), Decimal("1"), trade_date)
    buy_lines = db.query(JournalLine, Account).join(Account).filter(JournalLine.journal_entry_id == bought["journal_entry"].id).all()
    assert bought["journal_entry"].transaction_date == trade_date
    assert bought["journal_entry"].related_reference == f"portfolio:{portfolio.id}:security:{security.id}"
    assert {(account.code, line.debit, line.credit) for line, account in buy_lines} == {
        (1320, Decimal("51.00"), Decimal("0.00")),
        (1130, Decimal("0.00"), Decimal("51.00")),
    }

    sold = SellStockService(db, 1).sell(portfolio.id, broker.id, security.id, Decimal("10"), Decimal("6"), Decimal("1"), trade_date)
    sell_lines = db.query(JournalLine, Account).join(Account).filter(JournalLine.journal_entry_id == sold["journal_entry"].id).all()
    assert sold["journal_entry"].transaction_date == trade_date
    assert sum((line.debit for line, _ in sell_lines), Decimal("0")) == sum((line.credit for line, _ in sell_lines), Decimal("0"))
    assert {(account.code, line.debit, line.credit) for line, account in sell_lines} == {
        (1130, Decimal("59.00"), Decimal("0.00")),
        (1320, Decimal("0.00"), Decimal("51.00")),
        (5610, Decimal("1.00"), Decimal("0.00")),
        (4600, Decimal("0.00"), Decimal("9.00")),
    }
    assert portfolio.cash_balance == Decimal("1008.00")


def test_opening_portfolio_records_cost_and_cash_without_current_cash_flow():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id=1, email="opening@example.com", username="opening", full_name="Opening User")
    currency = Currency(code="SAR", name="Saudi Riyal", symbol="SAR")
    db.add_all([user, currency]); db.flush()
    entity = Entity(user_id=1, code="PERSONAL", name="Personal", entity_type="PERSONAL", base_currency_id=currency.id)
    strategy = PortfolioStrategy(code="BALANCED", name="Balanced")
    objective = PortfolioObjective(code="GROWTH", name="Growth")
    broker = Broker(user_id=1, code="ALINMA", name="Alinma Capital")
    db.add_all([entity, strategy, objective, broker]); db.flush()
    portfolio = Portfolio(code="CASHBACK", name="Alinma Cashback", entity_id=entity.id, broker_id=broker.id, strategy_id=strategy.id, objective_id=objective.id, base_currency_id=currency.id)
    security = Security(symbol="4700", name="Alkhabeer Income", security_type="REIT", exchange="SAUDI_EXCHANGE", currency_code="SAR")
    accounts = [
        Account(code=1130, name="Brokerage Cash", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=1320, name="Saudi Stocks", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=3150, name="Opening Balance Equity", account_type="EQUITY", normal_balance="CREDIT"),
    ]
    db.add_all([portfolio, security, *accounts]); db.commit()

    _, positions, entry = OpeningPortfolioService(db, 1).record(
        portfolio_id=portfolio.id,
        cash_balance=Decimal("1.22"),
        positions=[{"security_id": security.id, "quantity": Decimal("188"), "total_cost": Decimal("1095.83"), "market_price": Decimal("4.63")}],
        as_of_date=datetime.now(),
    )

    assert positions[0].average_cost.quantize(Decimal("0.000001")) == Decimal("5.828883")
    assert portfolio.cash_balance == Decimal("1.22")
    assert entry.related_reference == f"opening-portfolio:{portfolio.id}"
    lines = db.query(JournalLine, Account).join(Account).filter(JournalLine.journal_entry_id == entry.id).all()
    assert {(account.code, line.debit, line.credit) for line, account in lines} == {
        (1320, Decimal("1095.83"), Decimal("0.00")),
        (1130, Decimal("1.22"), Decimal("0.00")),
        (3150, Decimal("0.00"), Decimal("1097.05")),
    }
    summary = FinancialSummaryService(db, 1).get()
    assert summary["cash_inflow"] == Decimal("0.00")
    assert summary["cash_outflow"] == Decimal("0.00")
    opening_activity = next(item for item in summary["recent_activity"] if item["related_reference"] == f"opening-portfolio:{portfolio.id}")
    assert opening_activity["display_amount"] == Decimal("1097.05")

    marafiq = Security(symbol="2083", name="MARAFIQ", security_type="STOCK", exchange="SAUDI_EXCHANGE", currency_code="SAR")
    mulkia = Security(symbol="4336", name="MULKIA REIT", security_type="REIT", exchange="SAUDI_EXCHANGE", currency_code="SAR")
    db.add_all([marafiq, mulkia]); db.commit()
    _, correction = OpeningPortfolioService(db, 1).correct(
        portfolio_id=portfolio.id, cash_balance=Decimal("1.22"), as_of_date=datetime.now(),
        positions=[
            {"security_id": security.id, "quantity": Decimal("188"), "total_cost": Decimal("1095.83"), "market_price": Decimal("4.63")},
            {"security_id": marafiq.id, "quantity": Decimal("55"), "total_cost": Decimal("2787.83"), "market_price": Decimal("43.64")},
            {"security_id": mulkia.id, "quantity": Decimal("245"), "total_cost": Decimal("1204.00"), "market_price": Decimal("4.47")},
        ],
    )
    assert correction.related_reference == f"opening-portfolio-adjustment:{portfolio.id}"
    correction_lines = db.query(JournalLine, Account).join(Account).filter(JournalLine.journal_entry_id == correction.id).all()
    assert {(account.code, line.debit, line.credit) for line, account in correction_lines} == {
        (1320, Decimal("3991.83"), Decimal("0.00")),
        (3150, Decimal("0.00"), Decimal("3991.83")),
    }
    corrected_summary = FinancialSummaryService(db, 1).get()
    assert corrected_summary["cash_inflow"] == Decimal("0.00")
    assert corrected_summary["cash_outflow"] == Decimal("0.00")
    allocation = PortfolioEngine(db).get_summary(portfolio.id)["allocation_summary"]
    assert set(allocation) == {"STOCK", "REIT"}
    assert allocation["STOCK"] > 0
    assert allocation["REIT"] > 0
    assert allocation["STOCK"] + allocation["REIT"] == Decimal("1")


def test_opening_portfolio_supports_a_short_covered_call_with_contract_multiplier():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(id=1, email="options@example.com", username="options", full_name="Options User")
    currency = Currency(code="USD", name="US Dollar", symbol="$")
    db.add_all([user, currency]); db.flush()
    entity = Entity(user_id=1, code="PERSONAL", name="Personal", entity_type="PERSONAL", base_currency_id=currency.id)
    strategy = PortfolioStrategy(code="BALANCED", name="Balanced")
    objective = PortfolioObjective(code="GROWTH", name="Growth")
    broker = Broker(user_id=1, code="ALKHABEER", name="Alkhabeer Global")
    db.add_all([entity, strategy, objective, broker]); db.flush()
    portfolio = Portfolio(code="US", name="US Portfolio", entity_id=entity.id, broker_id=broker.id, strategy_id=strategy.id, objective_id=objective.id, base_currency_id=currency.id)
    gpty = Security(symbol="GPTY", name="YieldMax AI & Tech Portfolio Option Income ETF", security_type="ETF", exchange="NYSE_ARCA", currency_code="USD")
    zeta = Security(symbol="ZETA", name="Zeta Global Holdings Corp", security_type="STOCK", exchange="NYSE", currency_code="USD")
    call = Security(symbol="ZETA20261218C35", name="ZETA 18 Dec 2026 35 Call", security_type="OPTION", exchange="US_OPTIONS", currency_code="USD")
    accounts = [
        Account(code=1310, name="US Stocks", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=1330, name="ETFs", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=1340, name="Options", account_type="ASSET", normal_balance="DEBIT"),
        Account(code=3150, name="Opening Balance Equity", account_type="EQUITY", normal_balance="CREDIT"),
    ]
    db.add_all([portfolio, gpty, zeta, call, *accounts]); db.commit()

    _, positions, entry = OpeningPortfolioService(db, 1).record(
        portfolio_id=portfolio.id,
        cash_balance=Decimal("0"),
        positions=[
            {"security_id": gpty.id, "quantity": Decimal("150"), "total_cost": Decimal("7372.93"), "market_price": Decimal("43.689933")},
            {"security_id": zeta.id, "quantity": Decimal("300"), "total_cost": Decimal("7455.96"), "market_price": Decimal("29.94")},
            {"security_id": call.id, "quantity": Decimal("-3"), "total_cost": Decimal("-323.38"), "market_price": Decimal("2.25")},
        ],
        as_of_date=datetime(2026, 9, 23, 17, 30),
    )

    option_position = next(item for item in positions if item.security_id == call.id)
    assert option_position.quantity == Decimal("-3")
    assert option_position.average_cost.quantize(Decimal("0.000001")) == Decimal("1.077933")
    summary = PortfolioEngine(db).get_summary(portfolio.id)
    option = next(item for item in summary["positions"] if item["security_id"] == call.id)
    assert option["total_cost"] == Decimal("-323.38")
    assert option["market_value"] == Decimal("-675.00")
    assert option["unrealized_pl"] == Decimal("-351.62")
    assert option["allocation_type"] == "COVERED_CALL"
    assert summary["allocation_summary"].get("OPTION") is None
    assert summary["allocation_summary"]["COVERED_CALL"] < 0
    assert summary["summary"]["total_cost"] == Decimal("14505.51")
    assert summary["summary"]["market_value"].quantize(Decimal("0.01")) == Decimal("14860.49")
    lines = db.query(JournalLine, Account).join(Account).filter(JournalLine.journal_entry_id == entry.id).all()
    assert {(account.code, line.debit, line.credit) for line, account in lines} == {
        (1330, Decimal("7372.93"), Decimal("0.00")),
        (1310, Decimal("7455.96"), Decimal("0.00")),
        (1340, Decimal("0.00"), Decimal("323.38")),
        (3150, Decimal("0.00"), Decimal("14505.51")),
    }
