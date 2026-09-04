from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
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
from app.accounting.schemas.loan import LoanRequest, LoanRefinanceRequest, LoanSettlementRequest, LoanUpdateRequest
from app.accounting.services.loan_service import LoanService
from app.accounting.services.financial_summary_service import FinancialSummaryService
from app.accounting.models.account import Account
from app.api.v1.account import current_user
from app.core.models.user import User
from app.accounting.models.credit_card_account import CreditCardAccount
from app.accounting.models.journal_entry import JournalEntry
from app.accounting.models.journal_line import JournalLine
from app.accounting.schemas.credit_card_account import CreditCardAccountRequest, CreditCardBalanceAdjustmentRequest, CreditCardUpdateRequest
from app.accounting.models.bank_account import BankAccount, BankAccountIdentifierAudit
from app.accounting.schemas.bank_account import BankAccountRequest, BankAccountUpdateRequest, BankOpeningBalanceRequest
from app.accounting.bank_identifiers import mask_bank_account_identifier, normalize_bank_account_identifier
from app.accounting.models.deposit import Deposit
from app.accounting.models.rental_schedule import RentalSchedule
from app.accounting.models.property_asset import PropertyAsset
from app.accounting.schemas.property_asset import PropertyUpdateRequest, PropertyValueAdjustmentRequest
from app.accounting.schemas.asset_disposition import BreakDepositRequest, SellPropertyRequest
from app.accounting.schemas.deposit import DepositBalanceAdjustmentRequest, DepositRequest, DepositUpdateRequest
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
        result.append({"id": entry.id, "reference": f"property:{entry.id}", "name": name, "usage": asset.usage if asset else "UNSPECIFIED", "income_type": asset.income_type if asset else None, "acquisition_cost": line.debit, "current_value": asset.current_value if asset else line.debit, "purchase_date": entry.transaction_date.date()})
    return result


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
    result = []
    for entry in entries:
        rows = db.query(JournalLine, Account).join(Account, JournalLine.account_id == Account.id).filter(JournalLine.journal_entry_id == entry.id).order_by(JournalLine.id).all()
        lines = [{"id": line.id, "account_code": account.code, "account_name": account.name, "debit": line.debit, "credit": line.credit} for line, account in rows]
        result.append({"id": entry.id, "transaction_date": entry.transaction_date, "description": entry.description, "related_reference": entry.related_reference, "created_at": entry.created_at, "lines": lines})
    return result


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
    return [{column.name: getattr(card, column.name) for column in card.__table__.columns} for card in cards]


@router.post("/credit-cards")
def create_credit_card(request: CreditCardAccountRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if request.used_balance > request.credit_limit:
        raise HTTPException(status_code=422, detail="لا يمكن أن يتجاوز الرصيد المستخدم الحد الائتماني.")
    if request.statement_balance is not None and request.statement_balance > request.used_balance:
        raise HTTPException(status_code=422, detail="لا يمكن أن يتجاوز رصيد كشف الحساب الرصيد المستخدم الحالي.")
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
                             is_fee_free=request.is_fee_free,
                             annual_fee=0 if request.is_fee_free else request.annual_fee,
                             fee_renewal_day=None if request.is_fee_free else request.fee_renewal_day,
                             fee_renewal_month=None if request.is_fee_free else request.fee_renewal_month,
                             currency_code=request.currency_code.upper())
    db.add(card)
    db.flush()
    if request.used_balance > 0:
        retained = db.query(Account).filter(Account.code.in_([3150, 3200])).order_by(Account.code).first()
        card_account = db.query(Account).filter(Account.code == 2110).one()
        entry = JournalEntry(user_id=user.id, description=f"رصيد افتتاحي · {card.card_name} •• {card.last4}",
                             transaction_date=request.as_of_date, related_reference=f"credit-card:{card.id}")
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
    card.card_name = request.card_name.strip()
    card.last4 = request.last4
    card.credit_limit = request.credit_limit
    card.minimum_monthly_payment = request.minimum_monthly_payment
    card.statement_balance = request.statement_balance
    card.currency_code = requested_currency
    card.statement_cutoff_day = request.statement_cutoff_day
    card.payment_due_day = request.payment_due_day
    card.is_fee_free = request.is_fee_free
    card.annual_fee = 0 if request.is_fee_free else request.annual_fee
    card.fee_renewal_day = None if request.is_fee_free else request.fee_renewal_day
    card.fee_renewal_month = None if request.is_fee_free else request.fee_renewal_month
    db.commit()
    db.refresh(card)
    return {column.name: getattr(card, column.name) for column in card.__table__.columns}


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
    if request.corrected_balance > card.credit_limit:
        raise HTTPException(status_code=422, detail="لا يمكن أن يتجاوز الرصيد المصحح الحد الائتماني.")
    difference = request.corrected_balance - card.current_balance
    if difference == 0:
        raise HTTPException(status_code=422, detail="The corrected balance is already the current balance.")
    retained = db.query(Account).filter(Account.code.in_([3250, 3200])).order_by(Account.code.desc()).first()
    card_account = db.query(Account).filter(Account.code == 2110).one()
    entry = JournalEntry(user_id=user.id, description=f"تسوية رصيد البطاقة الائتمانية · {card.card_name} •• {card.last4} · {request.reason.strip()}", transaction_date=request.adjustment_date, related_reference=f"credit-card-adjustment:{card.id}")
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
    items = db.query(BankAccount).filter(BankAccount.user_id == user.id).order_by(BankAccount.created_at).all()
    result = []
    for item in items:
        opening = _bank_opening_state(db, user.id, item.id)
        data = {column.name: getattr(item, column.name) for column in item.__table__.columns if column.name != "account_identifier_normalized"}
        data["account_identifier"] = mask_bank_account_identifier(item.account_identifier)
        data["display_name"] = f"{item.bank_name} {data['account_identifier']}"
        result.append({**data, **opening})
    return result


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
    has_accounts = db.query(BankAccount.id).filter(BankAccount.user_id == user.id).first() is not None
    if request.is_primary:
        db.query(BankAccount).filter(BankAccount.user_id == user.id).update({BankAccount.is_primary: False})
    account = BankAccount(user_id=user.id, bank_name=request.bank_name.strip(), account_type=request.account_type,
                          account_name=account_name, account_identifier=identifier, account_identifier_normalized=identifier,
                          current_balance=request.opening_balance,
                          currency_code=request.currency_code.upper(), is_primary=request.is_primary or not has_accounts)
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
    return {column.name: getattr(account, column.name) for column in account.__table__.columns if column.name != "account_identifier_normalized"}


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
    items = db.query(Deposit).filter(Deposit.user_id == user.id, Deposit.status == "ACTIVE").order_by(Deposit.created_at).all()
    return [{column.name: getattr(item, column.name) for column in item.__table__.columns} for item in items]


@router.post("/deposits")
def create_deposit(request: DepositRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    funding = db.query(BankAccount).filter(BankAccount.id == request.funding_bank_account_id, BankAccount.user_id == user.id).first()
    if funding is None:
        raise HTTPException(status_code=404, detail="Funding account was not found.")
    destination_id = request.income_bank_account_id or request.funding_bank_account_id
    destination = db.query(BankAccount).filter(BankAccount.id == destination_id, BankAccount.user_id == user.id).first()
    if destination is None:
        raise HTTPException(status_code=404, detail="Income destination account was not found.")
    currency = request.currency_code.upper()
    if funding.currency_code != currency or destination.currency_code != currency:
        raise HTTPException(status_code=422, detail="Deposit and selected bank accounts must use the same currency.")
    if request.principal_amount > funding.current_balance:
        raise HTTPException(status_code=422, detail="Deposit amount exceeds the selected bank account balance.")
    deposit = Deposit(
        user_id=user.id, provider_name=request.provider_name.strip(), product_name=request.product_name.strip(),
        product_type=request.product_type, funding_bank_account_id=funding.id, income_bank_account_id=destination.id,
        principal_amount=request.principal_amount, current_balance=request.principal_amount,
        annual_return_rate=request.annual_return_rate, payout_frequency=request.payout_frequency,
        start_date=request.start_date, maturity_date=request.maturity_date, auto_renew=request.auto_renew,
        currency_code=currency, status="ACTIVE",
    )
    db.add(deposit)
    db.flush()
    bank_ledger = db.query(Account).filter(Account.code == 1120).one()
    deposit_ledger = db.query(Account).filter(Account.code == 1160).first()
    if deposit_ledger is None:
        raise HTTPException(status_code=503, detail="The deposit ledger account is not configured. Apply the latest database update and try again.")
    entry = JournalEntry(user_id=user.id, description=f"Deposit funded · {deposit.product_name} · {deposit.provider_name}",
                         transaction_date=request.transaction_date, related_reference=f"deposit:{deposit.id}")
    db.add(entry)
    db.flush()
    db.add_all([
        JournalLine(journal_entry_id=entry.id, account_id=deposit_ledger.id, debit=request.principal_amount, credit=0),
        JournalLine(journal_entry_id=entry.id, account_id=bank_ledger.id, debit=0, credit=request.principal_amount),
    ])
    funding.current_balance -= request.principal_amount
    db.commit()
    db.refresh(deposit)
    return {column.name: getattr(deposit, column.name) for column in deposit.__table__.columns}


@router.patch("/deposits/{deposit_id}")
def update_deposit(deposit_id: int, request: DepositUpdateRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id, Deposit.user_id == user.id, Deposit.status == "ACTIVE").first()
    if deposit is None:
        raise HTTPException(status_code=404, detail="لم يتم العثور على الوديعة.")
    destination_id = request.income_bank_account_id or deposit.funding_bank_account_id
    destination = db.query(BankAccount).filter(BankAccount.id == destination_id, BankAccount.user_id == user.id).first()
    if destination is None:
        raise HTTPException(status_code=404, detail="Income destination account was not found.")
    if destination.currency_code != deposit.currency_code:
        raise HTTPException(status_code=422, detail="The income destination must use the deposit currency.")
    deposit.provider_name = request.provider_name.strip()
    deposit.product_name = request.product_name.strip()
    deposit.product_type = request.product_type
    deposit.income_bank_account_id = destination.id
    deposit.annual_return_rate = request.annual_return_rate
    deposit.payout_frequency = request.payout_frequency
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


@router.post("/deposits/{deposit_id}/balance-adjustment")
def adjust_deposit_balance(deposit_id: int, request: DepositBalanceAdjustmentRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id, Deposit.user_id == user.id, Deposit.status == "ACTIVE").first()
    if deposit is None:
        raise HTTPException(status_code=404, detail="Deposit was not found.")
    funding = db.query(BankAccount).filter(BankAccount.id == deposit.funding_bank_account_id, BankAccount.user_id == user.id).first()
    if funding is None:
        raise HTTPException(status_code=404, detail="The deposit funding account was not found.")
    difference = request.corrected_balance - deposit.current_balance
    if difference == 0:
        raise HTTPException(status_code=422, detail="The corrected balance is already the current balance.")
    if difference > 0 and difference > funding.current_balance:
        raise HTTPException(status_code=422, detail="The funding account does not have enough balance for this correction.")
    bank_ledger = db.query(Account).filter(Account.code == 1120).one()
    deposit_ledger = db.query(Account).filter(Account.code == 1160).one()
    amount = abs(difference)
    entry = JournalEntry(user_id=user.id, description=f"تسوية رصيد الوديعة · {deposit.product_name} · {request.reason.strip()}", transaction_date=request.adjustment_date, related_reference=f"deposit-adjustment:{deposit.id}")
    db.add(entry)
    db.flush()
    if difference > 0:
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


@router.post("/loans/{loan_id}/refinance")
def refinance_loan(loan_id: int, request: LoanRefinanceRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return loan_dict(LoanService(db, user.id).refinance(loan_id, request))
