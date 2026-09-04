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
from app.investing.application.sell_stock_service import SellStockService
from app.investing.models.broker import Broker
from app.investing.models.portfolio import Portfolio
from app.investing.models.portfolio_objective import PortfolioObjective
from app.investing.models.portfolio_strategy import PortfolioStrategy
from app.investing.models.security import Security


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

