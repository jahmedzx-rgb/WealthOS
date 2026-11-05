from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.accounting.services.bank_customer_service import customer_number, save_customer_number
from app.accounting.schemas.private_loan import PrivateLoanRequest, PrivateLoanPaymentRequest, PrivateLoanUpdateRequest, PrivateLoanPriorPaymentRequest, PrivateLoanPriorPaymentBulkRequest
from app.accounting.services.private_loan_service import PrivateLoanService
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.accounting.application.journal_entry import (
    JournalEntryUseCase,
)
from app.accounting.schemas.journal_entry import (
    JournalEntryRequest,
)
from app.accounting.application.buy_property import (
    BuyPropertyUseCase,
)
from app.accounting.schemas.buy_property import (
    BuyPropertyRequest,
)
from app.accounting.schemas.buy_asset import BuyAssetRequest
from app.accounting.services.buy_asset_service import BuyAssetService
from app.accounting.schemas.opening_cash import OpeningCashAdjustmentRequest, OpeningCashRequest
from app.accounting.schemas.inheritance import InheritanceRequest
from app.accounting.services.inheritance_service import InheritanceService
from app.accounting.application.card_payment import (
    CardPaymentUseCase,
)
from app.accounting.schemas.card_payment import (
    CardPaymentRequest,
)
from app.accounting.application.income import (
    IncomeUseCase,
)
from app.accounting.schemas.income import (
    IncomeRequest,
)
from app.accounting.application.add_cash import (
    AddCashUseCase,
)
from app.accounting.application.transfer import (
    TransferUseCase,
)
from app.accounting.application.withdraw_cash import (
    WithdrawCashUseCase,
)
from app.accounting.schemas.add_cash import (
    AddCashRequest,
)
from app.accounting.schemas.transfer import (
    TransferRequest,
)
from app.accounting.schemas.withdraw_cash import (
    WithdrawCashRequest,
)
from app.database.engine import get_db
from app.accounting.schemas.loan import LoanRequest, LoanRefinanceRequest, LoanSettlementRequest, LoanUpdateRequest, LoanPaymentRequest
from app.accounting.services.loan_service import LoanService
from app.accounting.services.financial_summary_service import FinancialSummaryService
from app.accounting.services.wealth_analytics_service import WealthAnalyticsService
from app.accounting.models.account import Account
from app.api.v1.account import current_user
from app.core.models.user import User
from app.accounting.models.credit_card_account import CreditCardAccount
from app.accounting.models.journal_entry import JournalEntry, JournalEntryDescriptionAudit
from app.accounting.models.journal_line import JournalLine
from app.accounting.schemas.credit_card_account import CreditCardAccountRequest, CreditCardBalanceAdjustmentRequest, CreditCardUpdateRequest
from app.accounting.models.bank_account import BankAccount, BankAccountIdentifierAudit
from app.accounting.schemas.bank_account import BankAccountRequest, BankAccountUpdateRequest, BankOpeningBalanceRequest
from app.accounting.bank_identifiers import mask_bank_account_identifier, normalize_bank_account_identifier
from app.accounting.models.deposit import Deposit
from app.accounting.models.loan import Loan
from app.accounting.models.rental_schedule import RentalSchedule
from app.accounting.models.property_asset import PropertyAsset
from app.accounting.schemas.property_asset import OpeningPropertyRequest, PropertyUpdateRequest, PropertyValueAdjustmentRequest
from app.accounting.services.opening_property_service import OpeningPropertyConflict, OpeningPropertyService
from app.accounting.schemas.asset_disposition import BreakDepositRequest, DepositMaturitySettlementRequest, SellPropertyRequest
from app.accounting.schemas.deposit import DepositBalanceAdjustmentRequest, DepositRequest, DepositReturnReconciliationRequest, DepositUpdateRequest, DepositWithdrawalRequest
from fastapi import HTTPException
from uuid import uuid4
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from copy import deepcopy
from app.accounting.services.reporting_service import ReportingService
from app.accounting.models.alternative_investment import AlternativeInvestment
from app.accounting.models.saving_circle import SavingCircle
from app.accounting.schemas.wealth_products import AlternativeInvestmentRequest, SavingCircleRequest
from app.accounting.services.wealth_product_service import WealthProductService
from app.accounting.schemas.expense import ExpenseRequest
from app.accounting.services.expense_service import ExpenseService
from app.accounting.services.card_statement_service import statement_view, reset_baseline, validate_card_date
from app.accounting.schemas.month_close import MonthCloseRequest, MonthReopenRequest
from app.accounting.services.month_close_service import MonthCloseService
from app.accounting.models.month_close import MonthClose
from app.accounting.models.bank_card import BankCard
from app.accounting.schemas.bank_card import BankCardRequest
from app.document_imports.models import ImportBatch, ImportedOperation


router = APIRouter(
    prefix="/accounting",
    tags=["Accounting"],
)


class ExpenseCreditCardCorrectionRequest(BaseModel):
    credit_card_id: int = Field(..., gt=0)


class CreditCardStatementCorrectionRequest(BaseModel):
    issued_statement_balance: Decimal = Field(ge=0)
    statement_cutoff_date: date


@router.post("/expense", status_code=201)
def record_expense(request: ExpenseRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        entry = ExpenseService(db, user.id).execute(request)
        return {
            "id": entry.id,
            "transaction_date": entry.transaction_date,
            "description": entry.description,
            "related_reference": entry.related_reference,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/expenses/{entry_id}/credit-card")
def correct_expense_credit_card(entry_id: int, request: ExpenseCreditCardCorrectionRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == user.id).with_for_update().first()
    if entry is None or not (entry.related_reference or "").startswith("credit-card-expense:"):
        raise HTTPException(status_code=404, detail="Credit card expense not found.")
    try:
        source_card_id = int(entry.related_reference.rsplit(":", 1)[1])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="The expense has an invalid credit card reference.") from exc
    if source_card_id == request.credit_card_id:
        raise HTTPException(status_code=422, detail="The expense is already assigned to this credit card.")
    cards = db.query(CreditCardAccount).filter(
        CreditCardAccount.id.in_([source_card_id, request.credit_card_id]),
        CreditCardAccount.user_id == user.id,
        CreditCardAccount.is_active.is_(True),
    ).with_for_update().all()
    cards_by_id = {card.id: card for card in cards}
    source_card = cards_by_id.get(source_card_id)
    target_card = cards_by_id.get(request.credit_card_id)
    if source_card is None or target_card is None:
        raise HTTPException(status_code=404, detail="Source or destination credit card not found.")
    liability_line = db.query(JournalLine).join(Account, JournalLine.account_id == Account.id).filter(
        JournalLine.journal_entry_id == entry.id,
        Account.code == 2110,
        JournalLine.credit > 0,
    ).one_or_none()
    if liability_line is None:
        raise HTTPException(status_code=422, detail="The expense liability amount could not be determined.")
    amount = liability_line.credit
    if source_card.current_balance < amount:
        raise HTTPException(status_code=422, detail="The source card balance is lower than this expense.")
    if target_card.current_balance + amount > target_card.credit_limit:
        raise HTTPException(status_code=422, detail="Moving this expense exceeds the destination card limit.")
    source_card.current_balance -= amount
    target_card.current_balance += amount
    entry.related_reference = f"credit-card-expense:{target_card.id}"
    db.commit()
    return {
        "entry_id": entry.id,
        "amount": amount,
        "source_card_id": source_card.id,
        "source_balance": source_card.current_balance,
        "credit_card_id": target_card.id,
        "credit_card_balance": target_card.current_balance,
    }


def _model_dict(item):
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}


@router.get("/saving-circles")
def saving_circles(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [_model_dict(item) for item in db.query(SavingCircle).filter(SavingCircle.user_id == user.id).order_by(SavingCircle.created_at.desc()).all()]


@router.post("/saving-circles", status_code=201)
def create_saving_circle(request: SavingCircleRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return _model_dict(WealthProductService(db, user.id).create_saving_circle(request))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/alternative-investments")
def alternative_investments(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [_model_dict(item) for item in db.query(AlternativeInvestment).filter(AlternativeInvestment.user_id == user.id).order_by(AlternativeInvestment.created_at.desc()).all()]


@router.post("/alternative-investments", status_code=201)
def create_alternative_investment(request: AlternativeInvestmentRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return _model_dict(WealthProductService(db, user.id).create_alternative(request))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/financial-summary")
def financial_summary(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return FinancialSummaryService(db, user.id).get()


@router.get("/wealth-analytics")
def wealth_analytics(period: str = "YTD", db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return WealthAnalyticsService(db, user.id).get(period.upper())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/activity")
def monthly_activity(year: int, month: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return FinancialSummaryService(db, user.id).activity_for_month(year, month)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/reports")
def financial_report(
    report_type: str,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    report_end = end_date or datetime.now(UTC).date()
    report_start = start_date or report_end.replace(day=1)
    try:
        return ReportingService(db, user.id).get(report_type, report_start, report_end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/reports/periodic")
def periodic_financial_reports(
    report_type: str,
    frequency: str = "MONTHLY",
    periods: int = 4,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if report_type not in {"balance_sheet", "cash_flow_statement"}:
        raise HTTPException(status_code=422, detail="Period comparison is available for the balance sheet and cash flow statement.")
    frequency = frequency.upper()
    limits = {"MONTHLY": 4, "QUARTERLY": 12, "ANNUAL": 10}
    if frequency not in limits:
        raise HTTPException(status_code=422, detail="Frequency must be monthly, quarterly, or annual.")
    if periods < 2 or periods > limits[frequency]:
        raise HTTPException(status_code=422, detail=f"Choose between 2 and {limits[frequency]} periods.")
    final_date = end_date or datetime.now(UTC).date()
    ranges: list[tuple[date, date, date, str, int]] = []
    cursor = final_date
    for _ in range(periods):
        if frequency == "MONTHLY":
            start = date(cursor.year, cursor.month, 1)
            next_period = date(start.year + (1 if start.month == 12 else 0), 1 if start.month == 12 else start.month + 1, 1)
            label, expected_months = start.strftime("%Y-%m"), 1
        elif frequency == "QUARTERLY":
            quarter = (cursor.month - 1) // 3 + 1
            start = date(cursor.year, (quarter - 1) * 3 + 1, 1)
            next_period = date(start.year + (1 if start.month == 10 else 0), 1 if start.month == 10 else start.month + 3, 1)
            label, expected_months = f"Q{quarter} {start.year}", 3
        else:
            start = date(cursor.year, 1, 1)
            next_period = date(start.year + 1, 1, 1)
            label, expected_months = str(start.year), 12
        natural_finish = next_period - timedelta(days=1)
        finish = min(cursor, natural_finish)
        ranges.append((start, finish, natural_finish, label, expected_months))
        cursor = start - timedelta(days=1)
    service = ReportingService(db, user.id)
    reports = []
    for start, finish, natural_finish, label, expected_months in reversed(ranges):
        report = service.get(report_type, start, finish)
        candidates = db.query(MonthClose).filter(MonthClose.user_id == user.id, MonthClose.status == "CLOSED", MonthClose.period_start >= start, MonthClose.period_end <= finish).order_by(MonthClose.period_end, MonthClose.version.desc()).all()
        latest_by_month = {}
        for item in candidates:
            latest_by_month.setdefault(item.period_end, item)
        saved = finish == natural_finish and len(latest_by_month) == expected_months
        source_snapshots = list(latest_by_month.values())
        if saved and report_type == "balance_sheet":
            report = deepcopy(source_snapshots[-1].snapshot[report_type])
        elif saved and report_type == "cash_flow_statement":
            combined = {}
            for snapshot in source_snapshots:
                for row in snapshot.snapshot[report_type]["rows"]:
                    key = (row.get("code"), row["label"], row["section"], row["is_total"])
                    if key not in combined:
                        combined[key] = deepcopy(row)
                        combined[key]["value"] = 0
                    combined[key]["value"] += row["value"]
            report = deepcopy(source_snapshots[0].snapshot[report_type])
            report["start_date"] = start
            report["end_date"] = finish
            report["rows"] = list(combined.values())
            report["source_entry_count"] = sum(item.snapshot[report_type]["source_entry_count"] for item in source_snapshots)
        reports.append({
            "period": label,
            "period_start": start,
            "period_end": finish,
            "status": "SAVED" if saved else "CURRENT",
            "snapshot_versions": [{"id": item.id, "version": item.version, "checksum": item.checksum, "period_end": item.period_end} for item in source_snapshots] if saved else [],
            "report": report,
        })
    return {"report_type": report_type, "frequency": frequency, "periods": reports}


@router.get("/month-closes/preview")
def month_close_preview(year: int, month: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return MonthCloseService(db, user.id).preview(year, month)
    except (ValueError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/month-closes")
def month_closes(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [_model_dict(item) for item in MonthCloseService(db, user.id).list()]


@router.post("/month-closes", status_code=201)
def close_month(request: MonthCloseRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return _model_dict(MonthCloseService(db, user.id).close(request.year, request.month))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/month-closes/{close_id}/reopen")
def reopen_month(close_id: int, request: MonthReopenRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return _model_dict(MonthCloseService(db, user.id).reopen(close_id, request.reason))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/properties")
def properties(db: Session = Depends(get_db), user: User = Depends(current_user)):
    classified = {item.acquisition_journal_entry_id: item for item in db.query(PropertyAsset).filter(PropertyAsset.user_id == user.id).all()}
    rows = (
        db.query(JournalEntry, JournalLine)
        .join(JournalLine, JournalLine.journal_entry_id == JournalEntry.id)
        .join(Account, Account.id == JournalLine.account_id)
        .filter(JournalEntry.user_id == user.id, Account.code == 1210, JournalLine.debit > 0)
        .order_by(JournalEntry.transaction_date.desc(), JournalEntry.id.desc())
        .all()
    )
    result = []
    for entry, line in rows:
        asset = classified.get(entry.id)
        if asset is not None and asset.status != "ACTIVE":
            continue
        name = asset.name if asset else (entry.description.removeprefix("Property Purchase:").split(" · Transfer Tax", 1)[0].strip() or entry.description)
        result.append({"id": entry.id, "reference": f"property:{entry.id}", "name": name, "usage": asset.usage if asset else "UNSPECIFIED", "income_type": asset.income_type if asset else None, "acquisition_cost": line.debit, "current_value": asset.current_value if asset else line.debit, "purchase_date": entry.transaction_date.date(), "acquisition_date": asset.acquisition_date if asset else None, "opening_date": asset.opening_date if asset else None})
    return result


@router.post("/properties/opening", status_code=201)
def create_opening_property(request: OpeningPropertyRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return OpeningPropertyService(db, user.id).execute(request)
    except OpeningPropertyConflict as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        try:
            return OpeningPropertyService(db, user.id).recover_idempotent_replay(request)
        except OpeningPropertyConflict as conflict:
            raise HTTPException(status_code=409, detail=str(conflict)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _property_record(db: Session, user_id: int, property_id: int):
    row = (db.query(JournalEntry, JournalLine).join(JournalLine, JournalLine.journal_entry_id == JournalEntry.id).join(Account, Account.id == JournalLine.account_id).filter(JournalEntry.id == property_id, JournalEntry.user_id == user_id, Account.code == 1210, JournalLine.debit > 0).first())
    if row is None:
        raise HTTPException(status_code=404, detail="Property was not found.")
    entry, line = row
    asset = db.query(PropertyAsset).filter(PropertyAsset.user_id == user_id, PropertyAsset.acquisition_journal_entry_id == property_id).first()
    if asset is None:
        name = entry.description.removeprefix("Property Purchase:").split(" · Transfer Tax", 1)[0].strip() or entry.description
        asset = PropertyAsset(user_id=user_id, acquisition_journal_entry_id=property_id, name=name, usage="UNSPECIFIED", current_value=line.debit, status="ACTIVE")
        db.add(asset)
        db.flush()
    return asset, entry, line


@router.patch("/properties/{property_id}")
def update_property(property_id: int, request: PropertyUpdateRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    asset, _, _ = _property_record(db, user.id, property_id)
    asset.name = request.property_name.strip()
    asset.usage = request.property_usage
    asset.income_type = request.property_income_type if request.property_usage == "INVESTMENT_PROPERTY" else None
    db.commit()
    return {"id": property_id, "reference": f"property:{property_id}", "name": asset.name, "usage": asset.usage, "income_type": asset.income_type, "current_value": asset.current_value}


@router.post("/properties/{property_id}/sell")
def sell_property(property_id: int, request: SellPropertyRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    asset, _, _ = _property_record(db, user.id, property_id)
    if asset.status != "ACTIVE":
        raise HTTPException(status_code=422, detail="This property is no longer active.")
    destination_ledger = db.query(Account).filter(Account.code == (1120 if request.payment_destination == "BANK_ACCOUNT" else 1110)).one()
    bank = None
    if request.payment_destination == "BANK_ACCOUNT":
        bank = db.query(BankAccount).filter(BankAccount.id == request.bank_account_id, BankAccount.user_id == user.id).first()
        if bank is None:
            raise HTTPException(status_code=404, detail="Destination bank account was not found.")
    property_ledger = db.query(Account).filter(Account.code == 1210).one()
    gain_ledger = db.query(Account).filter(Account.code == 4600).one()
    loss_ledger = db.query(Account).filter(Account.code == 5690).one()
    cost_ledger = db.query(Account).filter(Account.code == 5790).one()
    net_proceeds = request.sale_amount - request.selling_costs
    payment_label = {"BANK_TRANSFER": "Bank Transfer", "CHEQUE": "Cheque", "CASH": "Cash"}[request.payment_method]
    entry = JournalEntry(user_id=user.id, description=f"Property sale · {asset.name} · {payment_label} · {request.description.strip()}", transaction_date=request.transaction_date, related_reference=f"property-sale:{property_id}")
    db.add(entry); db.flush()
    lines = [JournalLine(journal_entry_id=entry.id, account_id=destination_ledger.id, debit=net_proceeds, credit=0), JournalLine(journal_entry_id=entry.id, account_id=property_ledger.id, debit=0, credit=asset.current_value)]
    if request.selling_costs > 0:
        lines.append(JournalLine(journal_entry_id=entry.id, account_id=cost_ledger.id, debit=request.selling_costs, credit=0))
    difference = request.sale_amount - asset.current_value
    if difference > 0:
        lines.append(JournalLine(journal_entry_id=entry.id, account_id=gain_ledger.id, debit=0, credit=difference))
    elif difference < 0:
        lines.append(JournalLine(journal_entry_id=entry.id, account_id=loss_ledger.id, debit=-difference, credit=0))
    db.add_all(lines)
    if bank is not None:
        bank.current_balance += net_proceeds
    asset.current_value = 0
    asset.status = "SOLD"
    db.query(RentalSchedule).filter(RentalSchedule.user_id == user.id, RentalSchedule.property_reference == f"property:{property_id}").update({RentalSchedule.active: False})
    db.commit()
    return {"message":"Property sale posted successfully.","property_id":property_id,"net_proceeds":net_proceeds}


@router.post("/properties/{property_id}/value-adjustment")
def adjust_property_value(property_id: int, request: PropertyValueAdjustmentRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    asset, _, _ = _property_record(db, user.id, property_id)
    difference = request.corrected_value - asset.current_value
    if difference == 0:
        raise HTTPException(status_code=422, detail="The corrected value matches the current property value.")
    property_ledger = db.query(Account).filter(Account.code == 1210).one()
    adjustment_equity = db.query(Account).filter(Account.code.in_([3250, 3200])).order_by(Account.code.desc()).first()
    entry = JournalEntry(user_id=user.id, description=f"Property value adjustment · {asset.name} · {request.reason.strip()}", transaction_date=request.adjustment_date, related_reference=f"property-adjustment:{property_id}")
    db.add(entry)
    db.flush()
    amount = abs(difference)
    if difference > 0:
        lines = [JournalLine(journal_entry_id=entry.id, account_id=property_ledger.id, debit=amount, credit=0), JournalLine(journal_entry_id=entry.id, account_id=adjustment_equity.id, debit=0, credit=amount)]
    else:
        lines = [JournalLine(journal_entry_id=entry.id, account_id=adjustment_equity.id, debit=amount, credit=0), JournalLine(journal_entry_id=entry.id, account_id=property_ledger.id, debit=0, credit=amount)]
    db.add_all(lines)
    asset.current_value = request.corrected_value
    db.commit()
    return {"id": property_id, "reference": f"property:{property_id}", "name": asset.name, "usage": asset.usage, "current_value": asset.current_value}


@router.get("/rental-reminders")
def rental_reminders(days: int = 30, db: Session = Depends(get_db), user: User = Depends(current_user)):
    today = date.today()
    horizon = today + timedelta(days=max(0, min(days, 365)))
    schedules = db.query(RentalSchedule).filter(
        RentalSchedule.user_id == user.id,
        RentalSchedule.active.is_(True),
        RentalSchedule.next_due_date <= horizon,
    ).order_by(RentalSchedule.next_due_date).all()
    return [{
        "id": item.id, "property_reference": item.property_reference, "property_name": item.property_name,
        "expected_amount": item.expected_amount, "frequency": item.frequency, "next_due_date": item.next_due_date,
        "destination_account_code": item.destination_account_code, "days_until": (item.next_due_date - today).days,
    } for item in schedules]


@router.get("/journal-entries")
def journal_entries(db: Session = Depends(get_db), user: User = Depends(current_user)):
    entries = db.query(JournalEntry).filter(JournalEntry.user_id == user.id).order_by(JournalEntry.transaction_date.desc(), JournalEntry.id.desc()).all()
    cards = {card.id: card for card in db.query(CreditCardAccount).filter(CreditCardAccount.user_id == user.id).all()}
    result = []
    for entry in entries:
        rows = db.query(JournalLine, Account).join(Account, JournalLine.account_id == Account.id).filter(JournalLine.journal_entry_id == entry.id).order_by(JournalLine.id).all()
        card_detail = None
        reference = entry.related_reference or ""
        if reference.startswith(("credit-card-expense:", "credit-card-cashback:", "credit-card-adjustment:", "credit-card:", "opening-credit-card:")):
            try:
                card = cards.get(int(reference.rsplit(":", 1)[1]))
                if card is not None:
                    card_detail = f"{card.issuer_bank} · {card.card_name} •• {card.last4}"
            except ValueError:
                pass
        lines = [{"id": line.id, "account_code": account.code, "account_name": account.name, "account_detail": card_detail if account.code == 2110 else None, "debit": line.debit, "credit": line.credit} for line, account in rows]
        edits = db.query(JournalEntryDescriptionAudit).filter(JournalEntryDescriptionAudit.journal_entry_id == entry.id, JournalEntryDescriptionAudit.user_id == user.id).order_by(JournalEntryDescriptionAudit.changed_at.desc(), JournalEntryDescriptionAudit.id.desc()).all()
        result.append({"id": entry.id, "transaction_date": entry.transaction_date, "description": entry.description, "related_reference": entry.related_reference, "created_at": entry.created_at, "description_edits": [{"id": edit.id, "previous_description": edit.previous_description, "new_description": edit.new_description, "changed_at": edit.changed_at} for edit in edits], "lines": lines})
    return result


class JournalEntryDescriptionUpdate(BaseModel):
    description: str = Field(min_length=3, max_length=255)


@router.patch("/journal-entries/{entry_id}/description")
def update_journal_entry_description(entry_id: int, request: JournalEntryDescriptionUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == user.id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Transaction was not found.")
    description = request.description.strip()
    if len(description) < 3:
        raise HTTPException(status_code=422, detail="Description must contain at least 3 characters.")
    if description == entry.description:
        raise HTTPException(status_code=422, detail="The description has not changed.")
    audit = JournalEntryDescriptionAudit(journal_entry_id=entry.id, user_id=user.id, previous_description=entry.description, new_description=description)
    entry.description = description
    db.add(audit); db.commit(); db.refresh(entry); db.refresh(audit)
    return {"id": entry.id, "description": entry.description, "description_edit": {"id": audit.id, "previous_description": audit.previous_description, "new_description": audit.new_description, "changed_at": audit.changed_at}}


def _imported_date(value: str | None):
    if not value:
        return None
    for parser in (
        lambda raw: datetime.fromisoformat(raw.replace("Z", "+00:00")).date(),
        lambda raw: datetime.strptime(raw[:10], "%d/%m/%Y").date(),
    ):
        try:
            return parser(value.strip())
        except ValueError:
            continue
    return None


@router.get("/reconciliation")
def reconciliation(db: Session = Depends(get_db), user: User = Depends(current_user)):
    imported = (
        db.query(ImportedOperation)
        .join(ImportBatch, ImportBatch.id == ImportedOperation.batch_id)
        .filter(ImportBatch.user_id == user.id, ImportedOperation.status != "IGNORED")
        .order_by(ImportedOperation.id.desc())
        .all()
    )
    entries = db.query(JournalEntry).filter(JournalEntry.user_id == user.id).all()
    entry_totals = {}
    for entry in entries:
        debit = sum((line.debit for line in db.query(JournalLine).filter(JournalLine.journal_entry_id == entry.id)), Decimal("0"))
        entry_totals[entry.id] = debit
    items = []
    for operation in imported:
        confirmed = operation.status == "CONFIRMED" and bool(operation.posting_reference)
        operation_date = _imported_date(operation.transaction_date)
        candidates = [] if confirmed else [
            entry for entry in entries
            if operation.amount is not None
            and abs(entry_totals[entry.id] - abs(operation.amount)) <= Decimal("0.01")
            and (operation_date is None or abs((entry.transaction_date.date() - operation_date).days) <= 1)
        ]
        candidate = candidates[0] if len(candidates) == 1 else None
        status = "MATCHED" if confirmed else "SUGGESTED" if candidate else "REVIEW"
        items.append({
            "id": operation.id,
            "date": operation.transaction_date,
            "description": operation.description,
            "amount": operation.amount,
            "currency": operation.currency or "SAR",
            "status": status,
            "posting_reference": operation.posting_reference,
            "journal_entry_id": candidate.id if candidate else None,
            "journal_description": candidate.description if candidate else None,
        })
    return {
        "matched": sum(item["status"] == "MATCHED" for item in items),
        "suggested": sum(item["status"] == "SUGGESTED" for item in items),
        "needs_review": sum(item["status"] == "REVIEW" for item in items),
        "items": items,
        "generated_at": datetime.now(UTC),
    }


@router.get("/credit-cards")
def list_credit_cards(db: Session = Depends(get_db), user: User = Depends(current_user)):
    cards = db.query(CreditCardAccount).filter(CreditCardAccount.user_id == user.id, CreditCardAccount.is_active.is_(True)).order_by(CreditCardAccount.created_at).all()
    return [{**{column.name: getattr(card, column.name) for column in card.__table__.columns}, **statement_view(db, card)} for card in cards]


@router.get("/credit-cards/{card_id}/payments")
def credit_card_payment_history(card_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    card = db.query(CreditCardAccount).filter(CreditCardAccount.id == card_id, CreditCardAccount.user_id == user.id).first()
    if card is None:
        raise HTTPException(status_code=404, detail="Credit card not found.")
    cards = db.query(CreditCardAccount).filter(CreditCardAccount.user_id == user.id).all()
    cards_by_id = {item.id: item for item in cards}
    entries = db.query(JournalEntry).filter(
        JournalEntry.user_id == user.id,
        or_(
            JournalEntry.related_reference == f"credit-card-payment:{card_id}",
            JournalEntry.related_reference.like(f"credit-card-sadad:%:{card_id}"),
            JournalEntry.related_reference.like(f"credit-card-sadad:{card_id}:%"),
        ),
    ).order_by(JournalEntry.transaction_date.desc(), JournalEntry.id.desc()).all()
    history = []
    for entry in entries:
        reference = entry.related_reference or ""
        lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == entry.id).all()
        amount = max((max(line.debit or 0, line.credit or 0) for line in lines), default=0)
        role, counterpart = "RECEIVED", "Bank account"
        if reference.startswith("credit-card-sadad:"):
            _, source_id, target_id = reference.split(":")
            source, target = cards_by_id.get(int(source_id)), cards_by_id.get(int(target_id))
            if int(source_id) == card_id:
                role, other = "FUNDED", target
            else:
                role, other = "RECEIVED", source
            counterpart = f"{other.issuer_bank} · {other.card_name} · •• {other.last4}" if other else "Credit card"
        history.append({"id": entry.id, "transaction_date": entry.transaction_date, "amount": amount,
                        "role": role, "counterpart": counterpart, "description": entry.description,
                        "activity_url": f"/activity/{entry.id}"})
    projected_statement = statement_view(db, card)
    cutoff_date = projected_statement.get("statement_cutoff_date")
    paid_since_statement = sum((item["amount"] for item in history if item["role"] == "RECEIVED" and (cutoff_date is None or item["transaction_date"].date() > cutoff_date)), 0)
    payment_by_entry = {item["id"]: item for item in history}
    transaction_entries = db.query(JournalEntry).filter(
        JournalEntry.user_id == user.id,
        or_(
            JournalEntry.related_reference.in_([
                f"credit-card-expense:{card_id}", f"credit-card-cashback:{card_id}",
                f"credit-card-adjustment:{card_id}", f"opening-credit-card:{card_id}", f"credit-card:{card_id}",
                f"credit-card-payment:{card_id}",
            ]),
            JournalEntry.related_reference.like(f"credit-card-sadad:%:{card_id}"),
            JournalEntry.related_reference.like(f"credit-card-sadad:{card_id}:%"),
        ),
    ).order_by(JournalEntry.transaction_date.desc(), JournalEntry.id.desc()).all()
    transactions = []
    for entry in transaction_entries:
        reference = entry.related_reference or ""
        payment = payment_by_entry.get(entry.id)
        if payment:
            effect = -payment["amount"] if payment["role"] == "RECEIVED" else payment["amount"]
            category = "PAYMENT_RECEIVED" if payment["role"] == "RECEIVED" else "PAYMENT_FUNDED"
            counterpart = payment["counterpart"]
        else:
            liability_lines = db.query(JournalLine).join(Account, JournalLine.account_id == Account.id).filter(JournalLine.journal_entry_id == entry.id, Account.code == 2110).all()
            effect = sum(((line.credit or 0) - (line.debit or 0) for line in liability_lines), 0)
            category = "PURCHASE" if reference.startswith("credit-card-expense:") else "CASHBACK" if reference.startswith("credit-card-cashback:") else "ADJUSTMENT" if reference.startswith("credit-card-adjustment:") else "OPENING_BALANCE"
            counterpart = None
        transactions.append({"id": entry.id, "transaction_date": entry.transaction_date, "amount": abs(effect), "balance_effect": effect,
                             "category": category, "counterpart": counterpart, "description": entry.description,
                             "related_reference": entry.related_reference, "is_payment": payment is not None, "activity_url": f"/activity/{entry.id}"})
    return {"card": {**{column.name: getattr(card, column.name) for column in card.__table__.columns}, **projected_statement}, "payments": history, "transactions": transactions, "paid_since_statement": paid_since_statement}


class CreditCardPaymentDateUpdate(BaseModel):
    transaction_date: datetime


@router.patch("/credit-cards/{card_id}/payments/{entry_id}")
def update_credit_card_payment_date(card_id: int, entry_id: int, request: CreditCardPaymentDateUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    card = db.query(CreditCardAccount).filter(CreditCardAccount.id == card_id, CreditCardAccount.user_id == user.id).first()
    if card is None:
        raise HTTPException(status_code=404, detail="Credit card not found.")
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == user.id).first()
    reference = entry.related_reference if entry else ""
    belongs_to_card = reference == f"credit-card-payment:{card_id}" or (
        reference.startswith("credit-card-sadad:") and str(card_id) in reference.split(":")[1:]
    )
    if entry is None or not belongs_to_card:
        raise HTTPException(status_code=404, detail="Card payment was not found.")
    corrected = request.transaction_date if request.transaction_date.tzinfo else request.transaction_date.replace(tzinfo=UTC)
    if corrected > datetime.now(UTC):
        raise HTTPException(status_code=422, detail="Payment date cannot be in the future.")
    entry.transaction_date = request.transaction_date
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "transaction_date": entry.transaction_date, "message": "Card payment date updated successfully."}


@router.delete("/credit-cards/{card_id}/payments/{entry_id}")
def delete_credit_card_payment(card_id: int, entry_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == user.id).with_for_update().first()
    reference = entry.related_reference if entry else ""
    if entry is None or not reference.startswith("credit-card-sadad:"):
        raise HTTPException(status_code=422, detail="Only card-to-card payments with an identifiable source can be deleted safely.")
    try:
        _, source_text, target_text = reference.split(":")
        source_id, target_id = int(source_text), int(target_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="The payment source could not be identified safely.") from exc
    if card_id not in {source_id, target_id}:
        raise HTTPException(status_code=404, detail="Card payment was not found.")
    cards = db.query(CreditCardAccount).filter(CreditCardAccount.user_id == user.id, CreditCardAccount.id.in_([source_id, target_id])).with_for_update().all()
    cards_by_id = {item.id: item for item in cards}
    source, target = cards_by_id.get(source_id), cards_by_id.get(target_id)
    if source is None or target is None:
        raise HTTPException(status_code=404, detail="Source or destination credit card was not found.")
    lines = db.query(JournalLine).filter(JournalLine.journal_entry_id == entry.id).all()
    amount = max((max(line.debit or 0, line.credit or 0) for line in lines), default=0)
    if source.current_balance < amount:
        raise HTTPException(status_code=409, detail="The funding card balance is now lower than this payment, so it cannot be deleted safely.")
    target.current_balance += amount
    target.statement_balance += amount
    source.current_balance -= amount
    source.statement_balance = max(0, source.statement_balance - amount)
    reset_baseline(target, target.statement_balance)
    reset_baseline(source, source.statement_balance)
    for line in lines:
        db.delete(line)
    db.delete(entry)
    db.commit()
    return {"message": "Card payment deleted successfully.", "amount": amount}


@router.post("/credit-cards")
def create_credit_card(request: CreditCardAccountRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if request.used_balance > request.credit_limit:
        raise HTTPException(status_code=422, detail="Credit used cannot exceed the credit limit.")
    if request.statement_balance is not None and request.statement_balance > request.used_balance:
        raise HTTPException(status_code=422, detail="Statement balance cannot exceed current credit used.")
    duplicate = db.query(CreditCardAccount).filter(CreditCardAccount.user_id == user.id, CreditCardAccount.last4 == request.last4).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="توجد بطاقة بهذه الأرقام الأربعة الأخيرة بالفعل.")
    card = CreditCardAccount(user_id=user.id, issuer_bank=request.issuer_bank.strip(), card_name=request.card_name.strip(),
                             last4=request.last4, credit_limit=request.credit_limit,
                             current_balance=request.used_balance,
                             statement_balance=request.used_balance if request.statement_balance is None else request.statement_balance,
                             minimum_monthly_payment=request.minimum_monthly_payment,
                             statement_cutoff_day=request.statement_cutoff_day,
                             payment_due_day=request.payment_due_day,
                             payment_due_date=request.payment_due_date,
                             statement_cutoff_date=request.statement_cutoff_date,
                             is_fee_free=request.is_fee_free,
                             annual_fee=0 if request.is_fee_free else request.annual_fee,
                             fee_renewal_day=None if request.is_fee_free else request.fee_renewal_day,
                             fee_renewal_month=None if request.is_fee_free else request.fee_renewal_month,
                             currency_code=request.currency_code.upper())
    reset_baseline(card, card.statement_balance)
    db.add(card)
    db.flush()
    if request.used_balance > 0:
        retained = db.query(Account).filter(Account.code.in_([3150, 3200])).order_by(Account.code).first()
        card_account = db.query(Account).filter(Account.code == 2110).one()
        entry = JournalEntry(user_id=user.id, description=f"رصيد افتتاحي · {card.card_name} •• {card.last4}",
                             transaction_date=request.as_of_date, related_reference=f"opening-credit-card:{card.id}")
        db.add(entry)
        db.flush()
        db.add_all([
            JournalLine(journal_entry_id=entry.id, account_id=retained.id, debit=request.used_balance, credit=0),
            JournalLine(journal_entry_id=entry.id, account_id=card_account.id, debit=0, credit=request.used_balance),
        ])
    db.commit()
    db.refresh(card)
    return {column.name: getattr(card, column.name) for column in card.__table__.columns}


@router.patch("/credit-cards/{card_id}")
def update_credit_card(card_id: int, request: CreditCardUpdateRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    card = db.query(CreditCardAccount).filter(CreditCardAccount.id == card_id, CreditCardAccount.user_id == user.id, CreditCardAccount.is_active.is_(True)).first()
    if not card:
        raise HTTPException(status_code=404, detail="لم يتم العثور على البطاقة الائتمانية.")
    if request.credit_limit < card.current_balance:
        raise HTTPException(status_code=422, detail="لا يمكن أن يكون الحد الائتماني أقل من الرصيد المستخدم الحالي.")
    if request.statement_balance > card.current_balance:
        raise HTTPException(status_code=422, detail="Statement balance cannot exceed the current used balance.")
    requested_currency = request.currency_code.upper()
    if requested_currency != card.currency_code and card.current_balance > 0:
        raise HTTPException(status_code=422, detail="سدّد رصيد البطاقة قبل تغيير عملتها.")
    duplicate = db.query(CreditCardAccount).filter(CreditCardAccount.user_id == user.id, CreditCardAccount.last4 == request.last4, CreditCardAccount.id != card_id).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Another card with these last four digits already exists.")
    card.issuer_bank = request.issuer_bank.strip()
    projected = statement_view(db, card)
    if request.statement_balance != projected['statement_balance'] or request.statement_cutoff_day != card.statement_cutoff_day:
        reset_baseline(card, request.statement_balance)
    card.card_name = request.card_name.strip()
    card.last4 = request.last4
    card.credit_limit = request.credit_limit
    card.minimum_monthly_payment = request.minimum_monthly_payment
    card.statement_balance = request.statement_balance
    card.currency_code = requested_currency
    card.statement_cutoff_day = request.statement_cutoff_day
    card.payment_due_day = request.payment_due_day
    if 'payment_due_date' in request.model_fields_set:
        card.payment_due_date = request.payment_due_date
    if 'statement_cutoff_date' in request.model_fields_set:
        card.statement_cutoff_date = request.statement_cutoff_date
    card.is_fee_free = request.is_fee_free
    card.annual_fee = 0 if request.is_fee_free else request.annual_fee
    card.fee_renewal_day = None if request.is_fee_free else request.fee_renewal_day
    card.fee_renewal_month = None if request.is_fee_free else request.fee_renewal_month
    db.commit()
    db.refresh(card)
    return {column.name: getattr(card, column.name) for column in card.__table__.columns}


@router.patch("/credit-cards/{card_id}/issued-statement")
def correct_issued_credit_card_statement(card_id: int, request: CreditCardStatementCorrectionRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    card = db.query(CreditCardAccount).filter(CreditCardAccount.id == card_id, CreditCardAccount.user_id == user.id, CreditCardAccount.is_active.is_(True)).first()
    if card is None:
        raise HTTPException(status_code=404, detail="Credit card not found.")
    if request.issued_statement_balance > card.credit_limit:
        raise HTTPException(status_code=422, detail="Issued statement balance cannot exceed the credit limit.")
    if request.statement_cutoff_date > date.today():
        raise HTTPException(status_code=422, detail="Statement cutoff date cannot be in the future.")
    card.auto_statement_opening_balance = request.issued_statement_balance
    card.auto_statement_opening_due = request.issued_statement_balance
    card.statement_cutoff_date = request.statement_cutoff_date
    projected = statement_view(db, card)
    card.statement_balance = projected["statement_balance"]
    card.payment_due_date = projected["payment_due_date"]
    db.commit()
    return {"id": card.id, **projected}


@router.delete("/credit-cards/{card_id}")
def close_credit_card(card_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    card = db.query(CreditCardAccount).filter(CreditCardAccount.id == card_id, CreditCardAccount.user_id == user.id, CreditCardAccount.is_active.is_(True)).first()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found.")
    if card.current_balance > 0:
        raise HTTPException(status_code=409, detail=f"Pay the full outstanding balance of {card.current_balance:.2f} {card.currency_code} before removing this card.")
    from datetime import UTC, datetime
    card.is_active = False
    card.closed_at = datetime.now(UTC)
    db.commit()
    return {"message": "تم إغلاق البطاقة الائتمانية بنجاح.", "card_id": card.id}


@router.post("/credit-cards/{card_id}/balance-adjustment")
def adjust_credit_card_balance(card_id: int, request: CreditCardBalanceAdjustmentRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    card = db.query(CreditCardAccount).filter(CreditCardAccount.id == card_id, CreditCardAccount.user_id == user.id, CreditCardAccount.is_active.is_(True)).first()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found.")
    try:
        validate_card_date(card, request.adjustment_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if request.corrected_balance > card.credit_limit:
        raise HTTPException(status_code=422, detail="Corrected balance cannot exceed the credit limit.")
    difference = request.corrected_balance - card.current_balance
    if difference == 0:
        raise HTTPException(status_code=422, detail="The corrected balance is already the current balance.")
    retained = db.query(Account).filter(Account.code.in_([3250, 3200])).order_by(Account.code.desc()).first()
    card_account = db.query(Account).filter(Account.code == 2110).one()
    entry = JournalEntry(user_id=user.id, description=f"Credit card balance adjustment · {card.card_name} •• {card.last4} · {request.reason.strip()}", transaction_date=request.adjustment_date, related_reference=f"credit-card-adjustment:{card.id}")
    db.add(entry)
    db.flush()
    amount = abs(difference)
    if difference > 0:
        lines = [JournalLine(journal_entry_id=entry.id, account_id=retained.id, debit=amount, credit=0), JournalLine(journal_entry_id=entry.id, account_id=card_account.id, debit=0, credit=amount)]
    else:
        lines = [JournalLine(journal_entry_id=entry.id, account_id=card_account.id, debit=amount, credit=0), JournalLine(journal_entry_id=entry.id, account_id=retained.id, debit=0, credit=amount)]
    db.add_all(lines)
    card.current_balance = request.corrected_balance
    card.statement_balance = min(card.statement_balance, request.corrected_balance)
    db.commit()
    db.refresh(card)
    return {column.name: getattr(card, column.name) for column in card.__table__.columns}


@router.get("/bank-accounts")
def list_bank_accounts(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = db.query(BankAccount).filter(BankAccount.user_id == user.id, BankAccount.account_type != "DIGITAL_WALLET").order_by(BankAccount.created_at).all()
    result = []
    for item in items:
        opening = _bank_opening_state(db, user.id, item.id)
        data = {column.name: getattr(item, column.name) for column in item.__table__.columns if column.name != "account_identifier_normalized"}
        data["account_identifier"] = mask_bank_account_identifier(item.account_identifier)
        data["display_name"] = f"{item.bank_name} {data['account_identifier']}"
        result.append({**data, **opening})
    return result


@router.get("/digital-wallets")
def list_digital_wallets(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = db.query(BankAccount).filter(BankAccount.user_id == user.id, BankAccount.account_type == "DIGITAL_WALLET").order_by(BankAccount.created_at).all()
    return [{**{column.name: getattr(item, column.name) for column in item.__table__.columns if column.name != "account_identifier_normalized"}, "account_identifier": mask_bank_account_identifier(item.account_identifier), "display_name": f"{item.bank_name} {mask_bank_account_identifier(item.account_identifier)}"} for item in items]


@router.post("/digital-wallets")
def create_digital_wallet(request: BankAccountRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    identifier = normalize_bank_account_identifier(request.account_identifier)
    if len(identifier) < 4:
        raise HTTPException(status_code=422, detail="Wallet number must contain at least 4 characters.")
    if db.query(BankAccount.id).filter(BankAccount.user_id == user.id, BankAccount.account_identifier_normalized == identifier).first():
        raise HTTPException(status_code=409, detail="This wallet is already registered.")
    wallet = BankAccount(user_id=user.id, bank_name=request.bank_name.strip(), account_type="DIGITAL_WALLET", account_name=(request.account_name or "").strip() or request.bank_name.strip(), account_identifier=identifier, account_identifier_normalized=identifier, current_balance=request.opening_balance, currency_code=request.currency_code.upper(), is_primary=False)
    db.add(wallet); db.flush()
    if request.opening_balance != 0:
        cash_ledger = db.query(Account).filter(Account.code == 1175).one()
        opening_equity = db.query(Account).filter(Account.code.in_([3150, 3200])).order_by(Account.code).first()
        entry = JournalEntry(user_id=user.id, description=f"Opening digital wallet balance · {wallet.account_name}", transaction_date=request.as_of_date, related_reference=f"opening-digital-wallet:{wallet.id}")
        db.add(entry); db.flush(); amount = abs(request.opening_balance)
        db.add_all([JournalLine(journal_entry_id=entry.id, account_id=cash_ledger.id, debit=amount if request.opening_balance > 0 else 0, credit=amount if request.opening_balance < 0 else 0), JournalLine(journal_entry_id=entry.id, account_id=opening_equity.id, debit=amount if request.opening_balance < 0 else 0, credit=amount if request.opening_balance > 0 else 0)])
    db.commit(); db.refresh(wallet)
    return {**{column.name: getattr(wallet, column.name) for column in wallet.__table__.columns if column.name != "account_identifier_normalized"}, "account_identifier": mask_bank_account_identifier(wallet.account_identifier)}


@router.put("/digital-wallets/{wallet_id}")
def update_digital_wallet(wallet_id: int, request: BankAccountUpdateRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    wallet = db.query(BankAccount).filter(BankAccount.id == wallet_id, BankAccount.user_id == user.id, BankAccount.account_type == "DIGITAL_WALLET").first()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Digital wallet not found.")
    identifier = normalize_bank_account_identifier(request.account_identifier)
    duplicate = db.query(BankAccount.id).filter(BankAccount.user_id == user.id, BankAccount.id != wallet.id, BankAccount.account_identifier_normalized == identifier).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="This wallet is already registered.")
    wallet.bank_name=request.bank_name.strip();wallet.account_name=(request.account_name or "").strip() or wallet.bank_name;wallet.account_identifier=identifier;wallet.account_identifier_normalized=identifier
    db.commit();db.refresh(wallet)
    return {**{column.name:getattr(wallet,column.name) for column in wallet.__table__.columns if column.name!="account_identifier_normalized"},"account_identifier":mask_bank_account_identifier(wallet.account_identifier)}


def _bank_opening_state(db: Session, user_id: int, bank_account_id: int) -> dict:
    opening_reference = f"opening-bank-account:{bank_account_id}"
    adjustment_prefix = f"opening-bank-account-adjustment:{bank_account_id}:"
    entries = db.query(JournalEntry).filter(
        JournalEntry.user_id == user_id,
        (JournalEntry.related_reference == opening_reference) | JournalEntry.related_reference.startswith(adjustment_prefix),
    ).order_by(JournalEntry.transaction_date, JournalEntry.id).all()
    bank_ledger = db.query(Account).filter(Account.code == 1120).one()
    entry_ids = [entry.id for entry in entries]
    lines = db.query(JournalLine).filter(JournalLine.journal_entry_id.in_(entry_ids), JournalLine.account_id == bank_ledger.id).all() if entry_ids else []
    initial = next((entry for entry in entries if entry.related_reference == opening_reference), None)
    opening_balance = sum((line.debit - line.credit for line in lines), start=Decimal("0"))
    return {
        "has_opening_balance": initial is not None,
        "opening_balance": opening_balance,
        "opening_balance_date": initial.transaction_date if initial is not None else None,
    }


@router.post("/bank-accounts")
def create_bank_account(request: BankAccountRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    identifier = normalize_bank_account_identifier(request.account_identifier)
    if len(identifier) < 4:
        raise HTTPException(status_code=422, detail="IBAN or account number must contain at least 4 characters.")
    duplicate = db.query(BankAccount).filter(BankAccount.user_id == user.id, BankAccount.account_identifier_normalized == identifier).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="This bank account is already registered. Merging requires a separate workflow.")
    account_name = (request.account_name or "").strip() or request.bank_name.strip()
    try:
        save_customer_number(db,user.id,request.bank_name,request.customer_number)
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409,detail=str(error)) from error
    if request.is_primary:
        db.query(BankAccount).filter(BankAccount.user_id == user.id).update({BankAccount.is_primary: False})
    account = BankAccount(user_id=user.id, bank_name=request.bank_name.strip(), account_type=request.account_type,
                          account_name=account_name, account_identifier=identifier, account_identifier_normalized=identifier,
                          current_balance=request.opening_balance,
                          currency_code=request.currency_code.upper(), is_primary=request.is_primary)
    db.add(account)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This bank account is already registered. Merging requires a separate workflow.") from exc
    if request.opening_balance != 0:
        bank_ledger = db.query(Account).filter(Account.code == 1120).one()
        retained = db.query(Account).filter(Account.code.in_([3150, 3200])).order_by(Account.code).first()
        entry = JournalEntry(user_id=user.id, description=f"رصيد افتتاحي · {account.account_name}",
                             transaction_date=request.as_of_date, related_reference=f"opening-bank-account:{account.id}")
        db.add(entry)
        db.flush()
        amount = abs(request.opening_balance)
        if request.opening_balance > 0:
            lines = [JournalLine(journal_entry_id=entry.id, account_id=bank_ledger.id, debit=amount, credit=0),
                     JournalLine(journal_entry_id=entry.id, account_id=retained.id, debit=0, credit=amount)]
        else:
            lines = [JournalLine(journal_entry_id=entry.id, account_id=retained.id, debit=amount, credit=0),
                     JournalLine(journal_entry_id=entry.id, account_id=bank_ledger.id, debit=0, credit=amount)]
        db.add_all(lines)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This bank account is already registered. Merging requires a separate workflow.") from exc
    db.refresh(account)
    data = {column.name: getattr(account, column.name) for column in account.__table__.columns if column.name != "account_identifier_normalized"}
    data["account_identifier"] = mask_bank_account_identifier(account.account_identifier)
    data["display_name"] = f"{account.bank_name} {data['account_identifier']}"
    return data


@router.get("/bank-accounts/{bank_account_id}")
def get_bank_account(bank_account_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    account = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.user_id == user.id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Bank account not found.")
    return {**{column.name: getattr(account, column.name) for column in account.__table__.columns if column.name != "account_identifier_normalized"}, 'customer_number':customer_number(db,user.id,account.bank_name)}


@router.put("/bank-accounts/{bank_account_id}")
def update_bank_account(bank_account_id: int, request: BankAccountUpdateRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    account = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.user_id == user.id).with_for_update().first()
    if account is None:
        raise HTTPException(status_code=404, detail="Bank account not found.")
    normalized = normalize_bank_account_identifier(request.account_identifier)
    duplicate = db.query(BankAccount.id).filter(BankAccount.user_id == user.id, BankAccount.id != account.id, BankAccount.account_identifier_normalized == normalized).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="This bank account is already registered. Merging requires a separate workflow.")
    previous = normalize_bank_account_identifier(account.account_identifier)
    if previous != normalized:
        db.add(BankAccountIdentifierAudit(bank_account_id=account.id, user_id=user.id, previous_last4=previous[-4:], new_last4=normalized[-4:], reason=request.correction_reason.strip()))
        account.account_identifier = normalized
        account.account_identifier_normalized = normalized
    account.bank_name = request.bank_name.strip()
    if 'customer_number' in request.model_fields_set:
        save_customer_number(db,user.id,account.bank_name,request.customer_number,replace=True)
    account.account_type = request.account_type
    account.account_name = (request.account_name or "").strip() or account.bank_name
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This bank account is already registered. Merging requires a separate workflow.") from exc
    db.refresh(account)
    return {column.name: getattr(account, column.name) for column in account.__table__.columns if column.name != "account_identifier_normalized"}


@router.get("/bank-account-duplicates")
def bank_account_duplicate_report(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Report historical duplicates without deleting, merging, or exposing full numbers."""
    accounts = db.query(BankAccount).filter(BankAccount.user_id == user.id).order_by(BankAccount.id).all()
    groups: dict[str, list[BankAccount]] = {}
    for account in accounts:
        normalized = normalize_bank_account_identifier(account.account_identifier)
        groups.setdefault(normalized, []).append(account)
    return [{"masked_identifier": mask_bank_account_identifier(identifier), "account_ids": [item.id for item in items], "count": len(items)} for identifier, items in groups.items() if len(items) > 1]


@router.post("/bank-accounts/{bank_account_id}/opening-balance")
def set_bank_opening_balance(bank_account_id: int, request: BankOpeningBalanceRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    bank = db.query(BankAccount).filter(BankAccount.id == bank_account_id, BankAccount.user_id == user.id).first()
    if bank is None:
        raise HTTPException(status_code=404, detail="لم يتم العثور على الحساب البنكي.")
    state = _bank_opening_state(db, user.id, bank.id)
    previous = Decimal(state["opening_balance"])
    difference = request.corrected_opening_balance - previous
    if difference == 0:
        raise HTTPException(status_code=422, detail="The corrected opening balance is already recorded.")

    original_date = state["opening_balance_date"]
    prior_period_adjustment = False
    if original_date is None:
        posting_date = request.opening_date
        reference = f"opening-bank-account:{bank.id}"
        description = f"Opening balance · {bank.account_name} · {request.reason.strip()}"
    else:
        closed = db.query(MonthClose.id).filter(
            MonthClose.user_id == user.id,
            MonthClose.status == "CLOSED",
            MonthClose.period_start <= original_date.date(),
            MonthClose.period_end >= original_date.date(),
        ).first() is not None
        prior_period_adjustment = closed
        posting_date = request.adjustment_date if closed else original_date
        reference = f"opening-bank-account-adjustment:{bank.id}:{uuid4().hex}"
        description = f"Opening balance correction · {bank.account_name} · {previous} to {request.corrected_opening_balance} · {request.reason.strip()}"

    bank_ledger = db.query(Account).filter(Account.code == 1120).one()
    opening_equity = db.query(Account).filter(Account.code == 3150).first()
    if opening_equity is None:
        raise HTTPException(status_code=503, detail="Opening balance equity is not configured.")
    entry = JournalEntry(user_id=user.id, description=description, transaction_date=posting_date, related_reference=reference)
    db.add(entry)
    db.flush()
    amount = abs(difference)
    if difference > 0:
        lines = [JournalLine(journal_entry_id=entry.id, account_id=bank_ledger.id, debit=amount, credit=0), JournalLine(journal_entry_id=entry.id, account_id=opening_equity.id, debit=0, credit=amount)]
    else:
        lines = [JournalLine(journal_entry_id=entry.id, account_id=opening_equity.id, debit=amount, credit=0), JournalLine(journal_entry_id=entry.id, account_id=bank_ledger.id, debit=0, credit=amount)]
    db.add_all(lines)
    bank.current_balance += difference
    db.commit()
    db.refresh(bank)
    return {
        "bank_account_id": bank.id,
        "previous_opening_balance": previous,
        "corrected_opening_balance": request.corrected_opening_balance,
        "difference_posted": difference,
        "current_balance": bank.current_balance,
        "posting_date": posting_date,
        "prior_period_adjustment": prior_period_adjustment,
        "journal_entry_id": entry.id,
    }


@router.get("/bank-cards")
def list_bank_cards(db: Session = Depends(get_db), user: User = Depends(current_user)):
    cards = db.query(BankCard).filter(BankCard.user_id == user.id).order_by(BankCard.created_at).all()
    return [_model_dict(card) for card in cards]


@router.post("/bank-cards", status_code=201)
def create_bank_card(request: BankCardRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    bank = db.query(BankAccount).filter(BankAccount.id == request.bank_account_id, BankAccount.user_id == user.id).first()
    if bank is None:
        raise HTTPException(status_code=404, detail="Linked bank account was not found.")
    duplicate = db.query(BankCard).filter(
        BankCard.user_id == user.id,
        BankCard.bank_account_id == bank.id,
        BankCard.last4 == request.last4,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="This debit card is already linked to the selected account.")
    card = BankCard(
        user_id=user.id,
        bank_account_id=bank.id,
        card_name=request.card_name.strip(),
        last4=request.last4,
        card_network=request.card_network.strip().upper(),
        currency_code=bank.currency_code,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return _model_dict(card)


@router.get("/deposits")
def list_deposits(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = db.query(Deposit).filter(Deposit.user_id == user.id).order_by(Deposit.created_at.desc()).all()
    result = []
    for item in items:
        latest_return = db.query(JournalEntry).filter(JournalEntry.user_id == user.id, JournalEntry.related_reference == f"deposit-return:{item.id}").order_by(JournalEntry.transaction_date.desc()).first()
        cumulative_return = db.query(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), 0)).join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id).join(Account, JournalLine.account_id == Account.id).filter(JournalEntry.user_id == user.id, JournalEntry.related_reference == f"deposit-return:{item.id}", Account.code == 4400).scalar() if item.product_type == "INCOME_SAVINGS" else item.actual_return
        result.append({**{column.name: getattr(item, column.name) for column in item.__table__.columns}, "actual_return": cumulative_return, "standard_annual_return_rate": item.annual_return_rate, "annual_return_rate": item.effective_annual_return_rate, "accrual_start_date": latest_return.transaction_date.date() if latest_return else item.start_date})
    return result


@router.post("/deposits")
def create_deposit(request: DepositRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    currency = request.currency_code.upper()
    funding = None
    if request.funding_bank_account_id is not None:
        funding = db.query(BankAccount).filter(BankAccount.id == request.funding_bank_account_id, BankAccount.user_id == user.id).first()
        if funding is None:
            raise HTTPException(status_code=404, detail="Funding account was not found.")
    destination_id = request.income_bank_account_id
    destination = db.query(BankAccount).filter(BankAccount.id == destination_id, BankAccount.user_id == user.id).first() if destination_id else None
    if request.income_bank_account_id is not None and destination is None:
        raise HTTPException(status_code=404, detail="Income destination account was not found.")
    if (funding is not None and funding.currency_code != currency) or (destination is not None and destination.currency_code != currency):
        raise HTTPException(status_code=422, detail="Deposit and selected bank accounts must use the same currency.")
    if request.recording_method == "BANK" and funding is None:
        raise HTTPException(status_code=422, detail="Funding account is required for a bank-funded deposit.")
    if funding is not None and request.recording_method == "BANK" and request.principal_amount > funding.current_balance:
        raise HTTPException(status_code=422, detail="Deposit amount exceeds the selected bank account balance.")
    deposit = Deposit(
        user_id=user.id, provider_name=request.provider_name.strip(), product_name=request.product_name.strip(),
        product_type=request.product_type, funding_bank_account_id=funding.id if funding else None, income_bank_account_id=destination.id if destination else None,
        principal_amount=request.principal_amount, current_balance=request.principal_amount,
        annual_return_rate=request.annual_return_rate, payout_frequency=request.payout_frequency,
        payout_schedule=[{"payout_date": item.payout_date.isoformat(), "amount": str(item.amount)} for item in request.payout_schedule],
        start_date=request.start_date, maturity_date=request.maturity_date, auto_renew=request.auto_renew,
        currency_code=currency, status="ACTIVE",
    )
    db.add(deposit)
    db.flush()
    bank_ledger = db.query(Account).filter(Account.code == 1120).one()
    deposit_ledger = db.query(Account).filter(Account.code == 1160).first()
    if deposit_ledger is None:
        raise HTTPException(status_code=503, detail="The deposit ledger account is not configured. Apply the latest database update and try again.")
    opening = request.recording_method == "OPENING"
    entry = JournalEntry(user_id=user.id, description=f"{'Opening deposit balance' if opening else 'Deposit funded'} · {deposit.product_name} · {deposit.provider_name}",
                         transaction_date=request.transaction_date, related_reference=f"{'opening-deposit' if opening else 'deposit'}:{deposit.id}")
    db.add(entry)
    db.flush()
    credit_ledger = db.query(Account).filter(Account.code == 3150).first() if opening else bank_ledger
    if credit_ledger is None:
        raise HTTPException(status_code=503, detail="Opening balance equity is not configured.")
    db.add_all([JournalLine(journal_entry_id=entry.id, account_id=deposit_ledger.id, debit=request.principal_amount, credit=0), JournalLine(journal_entry_id=entry.id, account_id=credit_ledger.id, debit=0, credit=request.principal_amount)])
    if not opening:
        funding.current_balance -= request.principal_amount
    db.commit()
    db.refresh(deposit)
    return {column.name: getattr(deposit, column.name) for column in deposit.__table__.columns}


@router.patch("/deposits/{deposit_id}")
def update_deposit(deposit_id: int, request: DepositUpdateRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id, Deposit.user_id == user.id, Deposit.status == "ACTIVE").first()
    if deposit is None:
        raise HTTPException(status_code=404, detail="لم يتم العثور على الوديعة.")
    destination_id = request.income_bank_account_id
    destination = db.query(BankAccount).filter(BankAccount.id == destination_id, BankAccount.user_id == user.id).first() if destination_id else None
    if request.income_bank_account_id is not None and destination is None:
        raise HTTPException(status_code=404, detail="Income destination account was not found.")
    if destination is not None and destination.currency_code != deposit.currency_code:
        raise HTTPException(status_code=422, detail="The income destination must use the deposit currency.")
    if request.source_loan_id is not None:
        source_loan = db.query(Loan).filter(Loan.id == request.source_loan_id, Loan.user_id == user.id).first()
        funding_bank = db.query(BankAccount).filter(BankAccount.id == request.historical_funding_bank_account_id, BankAccount.user_id == user.id).first()
        if source_loan is None:
            raise HTTPException(status_code=404, detail="Source loan was not found.")
        if funding_bank is None:
            raise HTTPException(status_code=404, detail="Historical receiving account was not found.")
        if funding_bank.currency_code != deposit.currency_code:
            raise HTTPException(status_code=422, detail="Deposit and historical receiving account must use the same currency.")
        if deposit.source_loan_id is not None and deposit.source_loan_id != source_loan.id:
            raise HTTPException(status_code=422, detail="This deposit is already linked to another source loan.")
        if deposit.source_loan_id is None:
            already_allocated = sum(((item.historical_funding_amount or item.principal_amount) for item in db.query(Deposit).filter(Deposit.user_id == user.id, Deposit.source_loan_id == source_loan.id, Deposit.id != deposit.id).all()), Decimal("0"))
            allocated = request.historical_funding_amount
            if allocated > deposit.principal_amount:
                raise HTTPException(status_code=422, detail="Historical funding amount cannot exceed the deposit principal.")
            if already_allocated + allocated > source_loan.amount_received:
                raise HTTPException(status_code=422, detail="Linked deposits cannot exceed the net loan proceeds received.")
            bank_ledger = db.query(Account).filter(Account.code == 1120).one()
            opening_equity = db.query(Account).filter(Account.code == 3150).one()
            historical_at = datetime.combine(request.historical_funding_date, datetime.min.time(), tzinfo=UTC)
            inflow = JournalEntry(user_id=user.id, description=f"Historical loan proceeds allocated to deposit · {source_loan.name}", transaction_date=historical_at, related_reference=f"opening-historical-link:loan:{source_loan.id}:deposit:{deposit.id}:bank-account:{funding_bank.id}:in")
            db.add(inflow); db.flush()
            db.add_all([JournalLine(journal_entry_id=inflow.id, account_id=bank_ledger.id, debit=allocated, credit=0), JournalLine(journal_entry_id=inflow.id, account_id=opening_equity.id, debit=0, credit=allocated)])
            outflow = JournalEntry(user_id=user.id, description=f"Historical deposit funding · {deposit.product_name}", transaction_date=historical_at, related_reference=f"opening-historical-link:loan:{source_loan.id}:deposit:{deposit.id}:bank-account:{funding_bank.id}:out")
            db.add(outflow); db.flush()
            db.add_all([JournalLine(journal_entry_id=outflow.id, account_id=opening_equity.id, debit=allocated, credit=0), JournalLine(journal_entry_id=outflow.id, account_id=bank_ledger.id, debit=0, credit=allocated)])
        deposit.source_loan_id = source_loan.id
        deposit.funding_bank_account_id = funding_bank.id
        deposit.historical_funding_date = request.historical_funding_date
        deposit.historical_funding_amount = request.historical_funding_amount
    deposit.provider_name = request.provider_name.strip()
    deposit.product_name = request.product_name.strip()
    deposit.product_type = request.product_type
    deposit.income_bank_account_id = destination.id if destination else None
    deposit.annual_return_rate = request.annual_return_rate
    deposit.payout_frequency = request.payout_frequency
    deposit.payout_schedule = [{"payout_date": item.payout_date.isoformat(), "amount": str(item.amount)} for item in request.payout_schedule]
    deposit.start_date = request.start_date
    deposit.maturity_date = request.maturity_date
    deposit.auto_renew = request.auto_renew
    db.commit()
    db.refresh(deposit)
    return {column.name: getattr(deposit, column.name) for column in deposit.__table__.columns}


@router.post("/deposits/{deposit_id}/break")
def break_deposit(deposit_id: int, request: BreakDepositRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id, Deposit.user_id == user.id, Deposit.status == "ACTIVE").first()
    if deposit is None:
        raise HTTPException(status_code=404, detail="Active deposit was not found.")
    if request.amount_received > deposit.current_balance:
        raise HTTPException(status_code=422, detail="Amount received cannot exceed the current deposit balance.")
    bank = db.query(BankAccount).filter(BankAccount.id == request.destination_bank_account_id, BankAccount.user_id == user.id).first()
    if bank is None:
        raise HTTPException(status_code=404, detail="لم يتم العثور على الحساب البنكي الوجهة.")
    if bank.currency_code != deposit.currency_code:
        raise HTTPException(status_code=422, detail="Destination account must use the deposit currency.")
    bank_ledger = db.query(Account).filter(Account.code == 1120).one()
    deposit_ledger = db.query(Account).filter(Account.code == 1160).one()
    loss_ledger = db.query(Account).filter(Account.code == 5790).one()
    entry = JournalEntry(user_id=user.id, description=f"فك وديعة · {deposit.product_name} · {request.reason.strip()}", transaction_date=request.transaction_date, related_reference=f"deposit-break:{deposit.id}")
    db.add(entry); db.flush()
    lines = [JournalLine(journal_entry_id=entry.id, account_id=bank_ledger.id, debit=request.amount_received, credit=0), JournalLine(journal_entry_id=entry.id, account_id=deposit_ledger.id, debit=0, credit=deposit.current_balance)]
    loss = deposit.current_balance - request.amount_received
    if loss > 0:
        lines.append(JournalLine(journal_entry_id=entry.id, account_id=loss_ledger.id, debit=loss, credit=0))
    db.add_all(lines)
    bank.current_balance += request.amount_received
    deposit.current_balance = 0
    deposit.status = "CLOSED"
    db.commit()
    return {"message":"تم فك الوديعة بنجاح.","deposit_id":deposit.id,"amount_received":request.amount_received,"closure_cost":loss}


@router.post("/deposits/{deposit_id}/settle-maturity")
def settle_deposit_maturity(deposit_id: int, request: DepositMaturitySettlementRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id, Deposit.user_id == user.id, Deposit.status.in_(["ACTIVE", "MATURED"])).first()
    if deposit is None:
        raise HTTPException(status_code=404, detail="Deposit awaiting maturity settlement was not found.")
    if deposit.maturity_date is None or request.transaction_date.date() < deposit.maturity_date:
        raise HTTPException(status_code=422, detail="The deposit cannot be settled before its maturity date.")
    if request.action == "PENDING":
        deposit.status = "MATURED"
        deposit.settlement_action = "PENDING"
        db.commit(); db.refresh(deposit)
        return {"message": "Deposit marked as awaiting settlement.", "deposit_id": deposit.id, "new_deposit_id": None, "principal": deposit.current_balance, "income": 0}

    bank = None
    if request.action in {"PAYOUT_ALL", "REINVEST_PRINCIPAL"}:
        bank = db.query(BankAccount).filter(BankAccount.id == request.destination_bank_account_id, BankAccount.user_id == user.id).first()
        if bank is None:
            raise HTTPException(status_code=404, detail="Destination bank account was not found.")
        if bank.currency_code != deposit.currency_code:
            raise HTTPException(status_code=422, detail="Destination account must use the deposit currency.")

    deposit_ledger = db.query(Account).filter(Account.code == 1160).one()
    income_ledger = db.query(Account).filter(Account.code == 4400).one()
    bank_ledger = db.query(Account).filter(Account.code == 1120).one()
    principal = deposit.current_balance
    income = request.actual_return
    new_deposit = None
    if request.action == "PAYOUT_ALL":
        principal_entry = JournalEntry(user_id=user.id, description=f"Deposit principal returned · {deposit.product_name}", transaction_date=request.transaction_date, related_reference=f"deposit-maturity:{deposit.id}:principal-return")
        db.add(principal_entry); db.flush()
        db.add_all([JournalLine(journal_entry_id=principal_entry.id, account_id=bank_ledger.id, debit=principal, credit=0), JournalLine(journal_entry_id=principal_entry.id, account_id=deposit_ledger.id, debit=0, credit=principal)])
        bank.current_balance += principal + income
    else:
        duration = max(1, (deposit.maturity_date - deposit.start_date).days)
        reinvested = principal + income if request.action in {"REINVEST_ALL", "PROVIDER_BALANCE"} else principal
        provider_balance = request.action == "PROVIDER_BALANCE"
        new_deposit = Deposit(user_id=user.id, provider_name=deposit.provider_name, product_name=request.provider_balance_name if provider_balance else deposit.product_name, product_type="INCOME_SAVINGS" if provider_balance else deposit.product_type, funding_bank_account_id=None if provider_balance else deposit.funding_bank_account_id, income_bank_account_id=None if provider_balance else deposit.income_bank_account_id, principal_amount=reinvested, current_balance=reinvested, annual_return_rate=request.provider_standard_rate if provider_balance else deposit.annual_return_rate, promotional_annual_return_rate=request.provider_annual_rate if provider_balance else None, promotional_rate_end_date=request.provider_promotional_end_date.date() if provider_balance else None, payout_frequency="DAILY" if provider_balance else deposit.payout_frequency, payout_schedule=[], start_date=request.transaction_date.date(), maturity_date=None if provider_balance else request.transaction_date.date() + timedelta(days=duration), auto_renew=False if provider_balance else deposit.auto_renew, currency_code=deposit.currency_code, status="ACTIVE")
        db.add(new_deposit); db.flush()
        if request.action == "REINVEST_PRINCIPAL":
            bank.current_balance += income
    if income > 0:
        income_entry = JournalEntry(user_id=user.id, description=f"Deposit income · {deposit.product_name}", transaction_date=request.transaction_date, related_reference=f"deposit-maturity:{deposit.id}:income")
        db.add(income_entry); db.flush()
        income_destination = deposit_ledger if request.action in {"REINVEST_ALL", "PROVIDER_BALANCE"} else bank_ledger
        db.add_all([JournalLine(journal_entry_id=income_entry.id, account_id=income_destination.id, debit=income, credit=0), JournalLine(journal_entry_id=income_entry.id, account_id=income_ledger.id, debit=0, credit=income)])
    deposit.current_balance = 0
    deposit.status = "RENEWED" if new_deposit else "CLOSED"
    deposit.settled_at = request.transaction_date
    deposit.settlement_action = request.action
    deposit.settlement_bank_account_id = bank.id if bank else None
    deposit.actual_return = income
    db.commit()
    return {"message": "Deposit maturity settled successfully.", "deposit_id": deposit.id, "new_deposit_id": new_deposit.id if new_deposit else None, "principal": principal, "income": income}


@router.post("/deposits/{deposit_id}/balance-adjustment")
def adjust_deposit_balance(deposit_id: int, request: DepositBalanceAdjustmentRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id, Deposit.user_id == user.id, Deposit.status == "ACTIVE").first()
    if deposit is None:
        raise HTTPException(status_code=404, detail="Deposit was not found.")
    funding = db.query(BankAccount).filter(BankAccount.id == deposit.funding_bank_account_id, BankAccount.user_id == user.id).first()
    difference = request.corrected_balance - deposit.current_balance
    if difference == 0:
        raise HTTPException(status_code=422, detail="The corrected balance is already the current balance.")
    if funding is not None and difference > 0 and difference > funding.current_balance:
        raise HTTPException(status_code=422, detail="The funding account does not have enough balance for this correction.")
    bank_ledger = db.query(Account).filter(Account.code == 1120).one()
    deposit_ledger = db.query(Account).filter(Account.code == 1160).one()
    adjustment_equity = None
    if funding is None:
        adjustment_equity = db.query(Account).filter(Account.code.in_([3250, 3200])).order_by(Account.code.desc()).first()
        if adjustment_equity is None:
            raise HTTPException(status_code=422, detail="A balance adjustment account is required for this correction.")
    amount = abs(difference)
    entry = JournalEntry(user_id=user.id, description=f"Deposit balance adjustment · {deposit.product_name} · {request.reason.strip()}", transaction_date=request.adjustment_date, related_reference=f"deposit-adjustment:{deposit.id}")
    db.add(entry)
    db.flush()
    if funding is None and difference > 0:
        lines = [JournalLine(journal_entry_id=entry.id, account_id=deposit_ledger.id, debit=amount, credit=0), JournalLine(journal_entry_id=entry.id, account_id=adjustment_equity.id, debit=0, credit=amount)]
    elif funding is None:
        lines = [JournalLine(journal_entry_id=entry.id, account_id=adjustment_equity.id, debit=amount, credit=0), JournalLine(journal_entry_id=entry.id, account_id=deposit_ledger.id, debit=0, credit=amount)]
    elif difference > 0:
        lines = [JournalLine(journal_entry_id=entry.id, account_id=deposit_ledger.id, debit=amount, credit=0), JournalLine(journal_entry_id=entry.id, account_id=bank_ledger.id, debit=0, credit=amount)]
        funding.current_balance -= amount
    else:
        lines = [JournalLine(journal_entry_id=entry.id, account_id=bank_ledger.id, debit=amount, credit=0), JournalLine(journal_entry_id=entry.id, account_id=deposit_ledger.id, debit=0, credit=amount)]
        funding.current_balance += amount
    db.add_all(lines)
    deposit.current_balance = request.corrected_balance
    deposit.principal_amount = request.corrected_balance
    db.commit()
    db.refresh(deposit)
    return {column.name: getattr(deposit, column.name) for column in deposit.__table__.columns}


@router.post("/deposits/{deposit_id}/reconcile-return")
def reconcile_deposit_return(deposit_id: int, request: DepositReturnReconciliationRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id, Deposit.user_id == user.id, Deposit.status == "ACTIVE", Deposit.product_type == "INCOME_SAVINGS").first()
    if deposit is None:
        raise HTTPException(status_code=404, detail="Active income savings balance was not found.")
    income = request.confirmed_balance - deposit.current_balance
    if income <= 0:
        raise HTTPException(status_code=422, detail="The confirmed balance must include a positive unrecorded return.")
    deposit_ledger = db.query(Account).filter(Account.code == 1160).one()
    income_ledger = db.query(Account).filter(Account.code == 4400).one()
    entry = JournalEntry(user_id=user.id, description=f"Deposit income reconciliation · {deposit.product_name}", transaction_date=request.transaction_date, related_reference=f"deposit-return:{deposit.id}")
    db.add(entry); db.flush()
    db.add_all([JournalLine(journal_entry_id=entry.id, account_id=deposit_ledger.id, debit=income, credit=0), JournalLine(journal_entry_id=entry.id, account_id=income_ledger.id, debit=0, credit=income)])
    deposit.current_balance = request.confirmed_balance
    deposit.principal_amount = request.confirmed_balance
    db.commit(); db.refresh(deposit)
    return {"message": "Deposit return reconciled successfully.", "deposit_id": deposit.id, "income": income, "current_balance": deposit.current_balance, "accrual_start_date": request.transaction_date.date()}


@router.post("/deposits/{deposit_id}/withdraw")
def withdraw_from_deposit(deposit_id: int, request: DepositWithdrawalRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id, Deposit.user_id == user.id, Deposit.status == "ACTIVE", Deposit.product_type == "INCOME_SAVINGS").with_for_update().first()
    if deposit is None:
        raise HTTPException(status_code=404, detail="Active income savings balance was not found.")
    bank = db.query(BankAccount).filter(BankAccount.id == request.destination_bank_account_id, BankAccount.user_id == user.id).with_for_update().first()
    if bank is None:
        raise HTTPException(status_code=404, detail="Destination bank account was not found.")
    if bank.currency_code != deposit.currency_code:
        raise HTTPException(status_code=422, detail="Destination account must use the deposit currency.")
    if request.confirmed_balance < deposit.current_balance:
        raise HTTPException(status_code=422, detail="The confirmed provider balance cannot be below the recorded deposit balance.")
    income = request.confirmed_balance - deposit.current_balance
    prior_income = db.query(func.coalesce(func.sum(JournalLine.credit - JournalLine.debit), 0)).join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id).join(Account, JournalLine.account_id == Account.id).filter(JournalEntry.user_id == user.id, JournalEntry.related_reference == f"deposit-return:{deposit.id}", Account.code == 4400).scalar()
    deposit_ledger = db.query(Account).filter(Account.code == 1160).one()
    income_ledger = db.query(Account).filter(Account.code == 4400).one()
    bank_ledger = db.query(Account).filter(Account.code == 1120).one()
    if income > 0:
        income_entry = JournalEntry(user_id=user.id, description=f"Deposit income reconciliation · {deposit.product_name}", transaction_date=request.transaction_date, related_reference=f"deposit-return:{deposit.id}")
        db.add(income_entry); db.flush()
        db.add_all([JournalLine(journal_entry_id=income_entry.id, account_id=deposit_ledger.id, debit=income, credit=0), JournalLine(journal_entry_id=income_entry.id, account_id=income_ledger.id, debit=0, credit=income)])
    withdrawal = JournalEntry(user_id=user.id, description=f"Deposit withdrawal · {deposit.product_name}", transaction_date=request.transaction_date, related_reference=f"deposit-withdrawal:{deposit.id}")
    db.add(withdrawal); db.flush()
    db.add_all([JournalLine(journal_entry_id=withdrawal.id, account_id=bank_ledger.id, debit=request.amount, credit=0), JournalLine(journal_entry_id=withdrawal.id, account_id=deposit_ledger.id, debit=0, credit=request.amount)])
    remaining_balance = request.confirmed_balance - request.amount
    deposit.current_balance = remaining_balance
    if request.close_deposit:
        deposit.status = "CLOSED"
        deposit.settled_at = request.transaction_date
        deposit.settlement_action = "PAYOUT_ALL"
        deposit.settlement_bank_account_id = bank.id
        deposit.actual_return = prior_income + income
    else:
        deposit.principal_amount = remaining_balance
    bank.current_balance += request.amount
    db.commit(); db.refresh(deposit)
    return {"message": "Income savings deposit closed successfully." if request.close_deposit else "Deposit withdrawal posted successfully.", "deposit_id": deposit.id, "income": income, "withdrawn": request.amount, "current_balance": deposit.current_balance, "bank_balance": bank.current_balance, "closed": request.close_deposit}


@router.get("/accounts")
def posting_accounts(db: Session = Depends(get_db)):
    accounts = db.query(Account).filter(Account.is_active.is_(True), Account.allow_posting.is_(True)).order_by(Account.code).all()
    return [{"id": account.id, "code": account.code, "name": account.name, "account_type": account.account_type, "is_cash_account": account.name in FinancialSummaryService.CASH_ACCOUNT_NAMES} for account in accounts]


@router.post("/add-cash")
def add_cash(
    request: AddCashRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    use_case = AddCashUseCase(db, user.id)

    try:
        return use_case.execute(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@router.post("/withdraw-cash")
def withdraw_cash(
    request: WithdrawCashRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    use_case = WithdrawCashUseCase(db, user.id)

    try:
        return use_case.execute(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@router.post("/transfer")
def transfer(
    request: TransferRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    use_case = TransferUseCase(db, user.id)
    try:
        return use_case.execute(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@router.post("/income")
def record_income(
    request: IncomeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    use_case = IncomeUseCase(db, user.id)
    try:
        return use_case.execute(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@router.post("/card-payment")
def card_payment(
    request: CardPaymentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    use_case = CardPaymentUseCase(db, user.id)
    try:
        return use_case.execute(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@router.post("/buy-property")
def buy_property(
    request: BuyPropertyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    use_case = BuyPropertyUseCase(db, user.id)
    try:
        return use_case.execute(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@router.post("/buy-asset")
def buy_asset(request: BuyAssetRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return BuyAssetService(db, user.id).execute(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@router.post("/opening-cash")
def opening_cash(request: OpeningCashRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    existing = db.query(JournalEntry).filter(JournalEntry.user_id == user.id, JournalEntry.related_reference == "opening-cash").first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Opening Cash On Hand is already established. Use a documented balance adjustment instead.")
    cash_account = db.query(Account).filter(Account.code == 1110).first()
    opening_equity = db.query(Account).filter(Account.code == 3150).first()
    if cash_account is None or opening_equity is None:
        raise HTTPException(status_code=503, detail="Cash or opening balance equity is not configured.")
    entry = JournalEntry(user_id=user.id, description=request.description, transaction_date=request.transaction_date, related_reference="opening-cash")
    db.add(entry)
    db.flush()
    db.add_all([
        JournalLine(journal_entry_id=entry.id, account_id=cash_account.id, debit=request.amount, credit=0),
        JournalLine(journal_entry_id=entry.id, account_id=opening_equity.id, debit=0, credit=request.amount),
    ])
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/opening-cash/status")
def opening_cash_status(db: Session = Depends(get_db), user: User = Depends(current_user)):
    cash_account = db.query(Account).filter(Account.code == 1110).first()
    if cash_account is None:
        raise HTTPException(status_code=503, detail="حساب النقد في الصندوق غير مهيأ.")
    balance = db.query(JournalLine).join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id).filter(JournalEntry.user_id == user.id, JournalLine.account_id == cash_account.id).all()
    initialized = db.query(JournalEntry).filter(JournalEntry.user_id == user.id, JournalEntry.related_reference == "opening-cash").first() is not None
    return {"initialized": initialized, "current_balance": sum((line.debit - line.credit for line in balance), start=0)}


@router.post("/opening-cash/adjustment")
def adjust_opening_cash(request: OpeningCashAdjustmentRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    cash_account = db.query(Account).filter(Account.code == 1110).first()
    opening_equity = db.query(Account).filter(Account.code == 3150).first()
    if cash_account is None or opening_equity is None:
        raise HTTPException(status_code=503, detail="Cash or opening balance equity is not configured.")
    initialized = db.query(JournalEntry).filter(JournalEntry.user_id == user.id, JournalEntry.related_reference == "opening-cash").first()
    if initialized is None:
        raise HTTPException(status_code=422, detail="Create the opening Cash On Hand asset before adjusting it.")
    cash_lines = db.query(JournalLine).join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id).filter(JournalEntry.user_id == user.id, JournalLine.account_id == cash_account.id).all()
    current_balance = sum((line.debit - line.credit for line in cash_lines), start=0)
    difference = request.corrected_balance - current_balance
    if difference == 0:
        raise HTTPException(status_code=422, detail="The corrected balance is already the current Cash On Hand balance.")
    entry = JournalEntry(user_id=user.id, description=f"تصحيح رصيد النقد في الصندوق · {request.reason.strip()}", transaction_date=request.transaction_date, related_reference="opening-cash-adjustment")
    db.add(entry); db.flush()
    if difference > 0:
        lines = [JournalLine(journal_entry_id=entry.id, account_id=cash_account.id, debit=difference, credit=0), JournalLine(journal_entry_id=entry.id, account_id=opening_equity.id, debit=0, credit=difference)]
    else:
        correction = -difference
        lines = [JournalLine(journal_entry_id=entry.id, account_id=cash_account.id, debit=0, credit=correction), JournalLine(journal_entry_id=entry.id, account_id=opening_equity.id, debit=correction, credit=0)]
    db.add_all(lines); db.commit(); db.refresh(entry)
    return {"message": "تمت تسوية رصيد النقد في الصندوق بنجاح.", "journal_entry_id": entry.id, "current_balance": request.corrected_balance}


@router.post("/inheritance")
def record_inheritance(request: InheritanceRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return InheritanceService(db, user.id).execute(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

@router.post("/journal-entry")
def journal_entry(
    request: JournalEntryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    use_case = JournalEntryUseCase(db, user.id)

    try:
        return use_case.execute(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/loans")
def create_loan(request: LoanRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    loan = LoanService(db, user.id).create(request)
    return {column.name: getattr(loan, column.name) for column in loan.__table__.columns}


@router.post('/private-loans')
def create_private_loan(request: PrivateLoanRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return loan_dict(PrivateLoanService(db, user.id).create(request))
    except (ValueError, IntegrityError) as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error) if isinstance(error, ValueError) else 'Conflicting request. Refresh and retry.') from error


@router.post('/private-loans/{loan_id}/payments')
def pay_private_loan(loan_id: int, request: PrivateLoanPaymentRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return loan_dict(PrivateLoanService(db, user.id).pay(loan_id, request))
    except (ValueError, IntegrityError) as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error) if isinstance(error, ValueError) else 'Conflicting request. Refresh and retry.') from error


@router.get('/private-loans/{loan_id}/history')
def private_loan_history(loan_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return PrivateLoanService(db, user.id).history(loan_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

@router.patch('/private-loans/{loan_id}')
def update_private_loan(loan_id: int, request: PrivateLoanUpdateRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return loan_dict(PrivateLoanService(db, user.id).update(loan_id, request))
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error

@router.post('/private-loans/{loan_id}/pre-opening-payments')
def add_private_loan_prior_payment(loan_id: int, request: PrivateLoanPriorPaymentRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return PrivateLoanService(db, user.id).add_prior_payment_detail(loan_id, request)
    except (ValueError, IntegrityError) as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error) if isinstance(error, ValueError) else 'Conflicting request. Refresh and retry.') from error

@router.post('/private-loans/{loan_id}/pre-opening-payments/bulk')
def add_private_loan_prior_payments(loan_id: int, request: PrivateLoanPriorPaymentBulkRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        return PrivateLoanService(db, user.id).add_prior_payment_details(loan_id, request)
    except (ValueError, IntegrityError) as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error) if isinstance(error, ValueError) else 'Conflicting request. Refresh and retry.') from error


@router.get("/loans")
def list_loans(db: Session = Depends(get_db), user: User = Depends(current_user)):
    loans = LoanService(db, user.id).list()
    return [{column.name: getattr(loan, column.name) for column in loan.__table__.columns} for loan in loans]


def loan_dict(loan):
    return {column.name: getattr(loan, column.name) for column in loan.__table__.columns}


@router.patch("/loans/{loan_id}")
def update_loan(loan_id: int, request: LoanUpdateRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return loan_dict(LoanService(db, user.id).update(loan_id, request))


@router.post("/loans/{loan_id}/void")
def void_loan(loan_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return loan_dict(LoanService(db, user.id).void(loan_id))


@router.post("/loans/{loan_id}/settle")
def settle_loan(loan_id: int, request: LoanSettlementRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return loan_dict(LoanService(db, user.id).settle(loan_id, request))


@router.post("/loans/{loan_id}/payments")
def record_loan_payment(loan_id: int, request: LoanPaymentRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        payment = LoanService(db, user.id).record_payment(loan_id, request)
        return {column.name: getattr(payment, column.name) for column in payment.__table__.columns}
    except (ValueError, IntegrityError) as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error) if isinstance(error, ValueError) else "Conflicting payment. Refresh and retry.") from error


@router.get("/loans/{loan_id}/payments")
def get_loan_payments(loan_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    try:
        payments = LoanService(db, user.id).payment_history(loan_id)
        return [{column.name: getattr(payment, column.name) for column in payment.__table__.columns} for payment in payments]
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/loans/{loan_id}/refinance")
def refinance_loan(loan_id: int, request: LoanRefinanceRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return loan_dict(LoanService(db, user.id).refinance(loan_id, request))
