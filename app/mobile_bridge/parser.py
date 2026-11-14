import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation


ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")
OTP_PATTERN = re.compile(r"otp|verification code|one.?time password|رمز (?:التحقق|التأكيد|التفعيل|التنشيط|لمرة واحدة)", re.I)
FINANCIAL_PATTERN = re.compile(r"transaction|purchase|payment|card|credit|debit|transfer|deposit|withdraw|balance|amount|sar|usd|عملية|شراء|دفع|سداد|بطاقة|ائتمان|مدى|حوالة|تحويل|إيداع|ايداع|سحب|رصيد|مبلغ|خصم|مشتريات|رسوم|راتب|توزيع|استلام", re.I)
AMOUNT_PATTERN = re.compile(r"(?:amount|المبلغ|مبلغ|بمبلغ|قيمة)\s*(?:(?:is|of)\s*)?(?::\s*)?(?:(?:SAR|ر\.?س|USD|\$|⃁)\s*)?([-+]?\s*\d[\d,]*(?:\.\d{1,2})?)", re.I)
CURRENCY_AMOUNT_PATTERN = re.compile(r"(?:SAR|ر\.?س|USD|\$|⃁)\s*([-+]?\s*\d[\d,]*(?:\.\d{1,2})?)|([-+]?\s*\d[\d,]*(?:\.\d{1,2})?)\s*(?:SAR|ر\.?س|USD|\$|⃁)", re.I)
LAST4_PATTERN = re.compile(r"(?:visa|mastercard|mada|card|بطاقة|مدى)[^\n]{0,45}?(?:\*+|x+|•+|ending\s+in|تنتهي\s*(?:بـ|ب)?|رقم\s*)?\s*(\d{4})\b", re.I)


@dataclass(frozen=True)
class ParsedFinancialMessage:
    operation_type: str
    description: str
    amount: Decimal | None
    currency: str | None
    transaction_date: str
    card_last4: str | None
    confidence: int
    source_text: str


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).translate(ARABIC_DIGITS).replace("\u200f", "").strip()


def classify(value: str) -> str:
    text = value.casefold()
    if re.search(r"reversal|reversed|refund|عكس شراء|استرجاع مبلغ", text):
        return "Unclassified"
    if re.search(r"cashback|استرداد نقدي|استرجاع نقدي", text):
        return "Income"
    if re.search(r"term deposit|fixed deposit|وديعة|مرابحة", text):
        return "Deposit"
    if re.search(r"credit card.{0,20}(?:payment|bill|settlement)|سداد.{0,40}بطاقة|بطاقة.{0,40}سداد", text):
        return "Card payment"
    if re.search(r"transfer|تحويل|حوالة|حواله", text):
        return "Transfer"
    if re.search(r"trade|shares?|stocks?|broker|شراء (?:أسهم|سهم|وحدات)|بيع (?:أسهم|سهم|وحدات)|تداول|أسهم", text):
        return "Trade"
    if re.search(r"dividend|salary|income|deposit interest|rent|توزيع|راتب|دخل|فائدة|ايجار|إيجار|إيداع|ايداع", text):
        return "Income"
    if re.search(r"point of sale|\bpos\b|mada|مدى|payment|purchase|شراء|fee|withdraw|فاتورة|مشتريات|رسوم|سحب|خصم", text):
        return "Expense"
    return "Unclassified"


def currency_from(value: str) -> str | None:
    if re.search(r"USD|\$", value, re.I):
        return "USD"
    if re.search(r"SAR|ر\.?س|⃁", value, re.I):
        return "SAR"
    return None


def amount_from(value: str) -> Decimal | None:
    matches = [match.group(1) for match in AMOUNT_PATTERN.finditer(value)]
    if not matches:
        matches = [match.group(1) or match.group(2) for match in CURRENCY_AMOUNT_PATTERN.finditer(value)]
    cleaned = []
    for token in matches:
        try:
            cleaned.append(Decimal(token.replace(" ", "").replace(",", "")))
        except (InvalidOperation, AttributeError):
            continue
    return cleaned[0] if len(cleaned) == 1 else None


def parse_financial_message(sender: str, body: str, received_at: datetime) -> ParsedFinancialMessage | None:
    clean_sender, clean_body = normalize(sender), normalize(body)
    if OTP_PATTERN.search(clean_body) or not FINANCIAL_PATTERN.search(clean_body):
        return None
    operation_type = classify(clean_body)
    amount = amount_from(clean_body)
    if operation_type == "Unclassified" and amount is None:
        return None
    currency = currency_from(clean_body)
    card_match = LAST4_PATTERN.search(clean_body)
    card_last4 = card_match.group(1) if card_match else None
    signals = sum((amount is not None, operation_type != "Unclassified", currency is not None, card_last4 is not None))
    local_time = received_at.astimezone()
    source_text = f"{local_time.isoformat(timespec='minutes')} | {clean_sender} | {clean_body}"
    description = f"{clean_sender} · {clean_body}"
    if len(description) > 220:
        description = f"{description[:217]}…"
    return ParsedFinancialMessage(
        operation_type=operation_type,
        description=description,
        amount=amount,
        currency=currency,
        transaction_date=local_time.isoformat(timespec="minutes"),
        card_last4=card_last4,
        confidence=min(96, 45 + signals * 13),
        source_text=source_text,
    )
