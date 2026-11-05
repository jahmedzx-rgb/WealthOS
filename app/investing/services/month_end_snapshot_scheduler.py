import asyncio
import logging
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone

from app.core.models.user import User
from app.database.engine import SessionLocal
from app.investing.models.portfolio_valuation_snapshot import PortfolioValuationSnapshot
from app.investing.models.portfolio import Portfolio
from app.investing.services.portfolio_history_service import PortfolioHistoryService
from app.investing.services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)
RIYADH = timezone(timedelta(hours=3))


def capture_month_end_snapshots(snapshot_date) -> None:
    """Refresh held securities once at month close and freeze each user's holdings."""
    with SessionLocal() as db:
        users = db.query(User).filter(User.is_active.is_(True)).all()
        portfolios_by_user = {
            user.id: [portfolio for portfolio in PortfolioService(db).list(user.id)
                      if portfolio.created_at.date() <= snapshot_date]
            for user in users
        }
        history = PortfolioHistoryService(db)
        for user_id, portfolios in portfolios_by_user.items():
            for portfolio in portfolios:
                try:
                    history.capture_month_end(user_id, portfolio.id, snapshot_date)
                except Exception:
                    logger.exception("Unable to freeze month-end portfolio %s for user %s", portfolio.id, user_id)
            try:
                history.capture_month_end(user_id, None, snapshot_date)
            except Exception:
                logger.exception("Unable to freeze consolidated month-end snapshot for user %s", user_id)


def backfill_previous_month_if_needed() -> None:
    """Recover a month close if WealthOS was not running at the end of that month."""
    now = datetime.now(RIYADH)
    previous_month = date(now.year, now.month, 1) - timedelta(days=1)
    snapshot_date = previous_month
    with SessionLocal() as db:
        users = db.query(User).filter(User.is_active.is_(True)).all()
        needs_capture = False
        for user in users:
            snapshot = db.query(PortfolioValuationSnapshot).filter(
                PortfolioValuationSnapshot.user_id == user.id,
                PortfolioValuationSnapshot.portfolio_id.is_(None),
                PortfolioValuationSnapshot.valuation_date == snapshot_date,
            ).first()
            # Once the historical close has been saved, do not repeat a network-heavy
            # backfill on every launch just because an instrument was not priced.
            if snapshot is None or not snapshot.is_month_end or snapshot.positions_snapshot is None:
                needs_capture = True
                break
    if needs_capture:
        capture_month_end_snapshots(snapshot_date)


async def month_end_snapshot_loop() -> None:
    """At 23:59 Riyadh time on the calendar's last day, capture and freeze prices."""
    captured_date = None
    try:
        await asyncio.to_thread(backfill_previous_month_if_needed)
    except Exception:
        logger.exception("Previous month-end snapshot recovery failed")
    while True:
        now = datetime.now(RIYADH)
        is_last_day = now.day == monthrange(now.year, now.month)[1]
        if is_last_day and now.hour == 23 and now.minute >= 59 and captured_date != now.date():
            captured_date = now.date()
            try:
                await asyncio.to_thread(capture_month_end_snapshots, captured_date)
            except Exception:
                logger.exception("Month-end portfolio snapshot job failed for %s", captured_date)
        await asyncio.sleep(15)
