from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/src"
MODULE_PAGE = (FRONTEND / "pages/ModulePage.tsx").read_text(encoding="utf-8")
CARD_ACCOUNT = (FRONTEND / "operations/CreditCardAccountOperation.tsx").read_text(encoding="utf-8")
CARD_PAYMENT = (FRONTEND / "operations/CardPaymentOperation.tsx").read_text(encoding="utf-8")
LANGUAGE_CONTEXT = (FRONTEND / "context/LanguageContext.tsx").read_text(encoding="utf-8")


CARD_PAGE_COPY = {
    "Credit management", "Credit Cards", "Track balances, utilization, statements, and upcoming payments.",
    "Credit Used", "Available Credit", "Utilization", "Posted Cards", "Of", "Total Limit",
    "Monthly DBR Obligation", "Payment Due", "Day", "Billing Dates Not Set", "Edit", "Remove",
    "Pay credit card", "Record a card payment", "Add credit card", "Connect a new card",
    "Review statement", "Reconcile recent charges",
}

CARD_OPERATION_COPY = {
    "Edit Credit Card", "Card position", "Credit limit", "Available credit", "Utilization",
    "Credit Used", "Statement Balance", "Financial impact", "Credit used", "Monthly DBR obligation",
    "Add Credit Card", "Credit Card Payment", "Select Credit Card", "Credit Card Payment Posted Successfully.",
    "Unable to post the card payment.",
}


def _missing(copy: set[str]) -> list[str]:
    return sorted(value for value in copy if f"'{value}':" not in LANGUAGE_CONTEXT)


def test_credit_card_page_and_actions_use_language_context():
    assert "useLanguage" in MODULE_PAGE
    for label in ("Credit Used", "Available Credit", "Utilization"):
        assert f"t('{label}')" in MODULE_PAGE
    for label in ("Posted Cards", "Of", "Total Limit", "Monthly DBR Obligation", "Payment Due", "Day", "Billing Dates Not Set", "Edit", "Remove"):
        assert f"t('{label}')" in MODULE_PAGE


def test_credit_card_page_system_copy_has_arabic_equivalents():
    assert _missing(CARD_PAGE_COPY) == []


def test_credit_card_account_and_payment_operations_are_locale_aware():
    for source in (CARD_ACCOUNT, CARD_PAYMENT):
        assert "useLanguage" in source
        assert "t(" in source
    assert _missing(CARD_OPERATION_COPY) == []


def test_credit_card_names_and_bank_names_remain_user_data():
    for source in (MODULE_PAGE, CARD_ACCOUNT, CARD_PAYMENT):
        assert "t(card.card_name)" not in source
        assert "t(form.card_name)" not in source
        assert "t(form.issuer_bank)" not in source
    assert "{card.card_name}" in MODULE_PAGE
    assert "{card.card_name}" in CARD_PAYMENT


def test_credit_card_routes_inherit_global_rtl_including_dates():
    global_css = (FRONTEND / "index.css").read_text(encoding="utf-8")
    assert "[dir='rtl'] input[type='date']" in global_css
    assert "[dir='rtl'] input[type='datetime-local']" in global_css
    assert "direction: rtl" in global_css
