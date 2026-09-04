from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"
DEPOSITS_PAGE = (FRONTEND / "pages" / "DepositsPage.tsx").read_text(encoding="utf-8")
DEPOSIT_OPERATION = (FRONTEND / "operations" / "DepositOperation.tsx").read_text(encoding="utf-8")
DISPOSITION_OPERATION = (FRONTEND / "operations" / "AssetDispositionOperation.tsx").read_text(encoding="utf-8")
WORKSPACE_PAGE = (FRONTEND / "pages" / "OperationWorkspacePage.tsx").read_text(encoding="utf-8")
OPERATION_REGISTRY = (FRONTEND / "operations" / "operationRegistry.ts").read_text(encoding="utf-8")
LANGUAGE_CONTEXT = (FRONTEND / "context" / "LanguageContext.tsx").read_text(encoding="utf-8")


DEPOSIT_PAGE_COPY = {
    "Investment Assets", "Deposits", "Review balances, expected returns, payout schedules, and maturity dates.",
    "Add Deposit", "Active Deposits", "Currently Tracked", "Total Balance", "Posted Deposit Assets",
    "Weighted Annual Return", "Next Maturity", "No Maturity Date",
    "Deposit Positions", "Every active deposit and savings product recorded in WealthOS.",
    "Deposit", "Balance", "Return", "Maturity", "Modify", "Edit", "Break", "Open Ended",
    "No Deposits Yet", "Add a deposit to track its balance, return, and maturity.",
    "Loading deposits…", "Unable to load deposits",
}

DEPOSIT_FORM_COPY = {
    "Edit Deposit", "Deposit Details", "Current Deposit Balance", "Term Deposit", "Income-Producing Savings",
    "Provider Not Selected", "Deposit Position", "Financial Impact", "Estimated Return", "Maturity",
    "Open Ended", "Funding Account", "Not Selected", "Provider", "Product Name", "Product Type",
    "Select Bank Account", "Deposit Amount", "Currency", "Select Funding Account", "Income Destination",
    "Annual Return %", "Payout Frequency", "Monthly", "Quarterly", "At Maturity",
    "Start Date", "Maturity Date", "Optional", "Funding Date", "Adjust Balance", "Auto Renew",
    "Renew the principal at maturity", "Estimated Annual Return", "Add a bank account before creating a deposit.",
    "Save Changes", "Saving…", "Deposit not found.", "Complete the required deposit details.",
    "Deposit details updated successfully.", "Deposit created and funded successfully.",
    "Unable to save the deposit.", "Enter a valid corrected balance.",
    "Enter a valid adjustment date and a brief reason.",
    "Deposit balance adjusted and the accounting correction was posted.",
    "Unable to adjust the deposit balance.",
}

BREAK_DEPOSIT_COPY = {
    "Break Deposit", "Closes the deposit and returns the actual settlement to the selected bank account.",
    "Select Deposit", "Destination Bank Account", "Amount Received", "Transaction Date", "Reason",
    "Current Deposit Balance", "Post Break Deposit", "Break Deposit Posted Successfully.",
    "Active deposit was not found.", "Amount received cannot exceed the current deposit balance.",
    "Destination bank account was not found.", "Destination account must use the deposit currency.",
}


def _missing_translation_keys(copy: set[str]) -> list[str]:
    return sorted(value for value in copy if f"'{value}':" not in LANGUAGE_CONTEXT)


def test_every_deposit_route_uses_the_active_language_context():
    for source in (DEPOSITS_PAGE, DEPOSIT_OPERATION, DISPOSITION_OPERATION, WORKSPACE_PAGE):
        assert "useLanguage" in source
        assert "t(" in source


def test_deposit_page_system_copy_has_arabic_translations():
    assert _missing_translation_keys(DEPOSIT_PAGE_COPY) == []


def test_add_edit_and_balance_adjustment_system_copy_has_arabic_translations():
    assert _missing_translation_keys(DEPOSIT_FORM_COPY) == []


def test_break_deposit_system_copy_has_arabic_translations():
    assert _missing_translation_keys(BREAK_DEPOSIT_COPY) == []


def test_deposit_and_provider_names_remain_untranslated_user_data():
    # User-entered values are bound and rendered directly; only surrounding labels use t().
    assert "value={form.provider_name}" in DEPOSIT_OPERATION
    assert "value={form.product_name}" in DEPOSIT_OPERATION
    assert "t(form.provider_name)" not in DEPOSIT_OPERATION
    assert "t(form.product_name)" not in DEPOSIT_OPERATION
    assert "item.product_name" in DEPOSITS_PAGE
    assert "item.provider_name" in DEPOSITS_PAGE
    assert "t(item.product_name)" not in DEPOSITS_PAGE
    assert "t(item.provider_name)" not in DEPOSITS_PAGE
    assert ":item.product_name" in DISPOSITION_OPERATION
    assert ":item.provider_name" in DISPOSITION_OPERATION


def test_free_form_adjustment_and_break_reasons_are_not_translated():
    assert "reason:adjustment.reason.trim()" in DEPOSIT_OPERATION
    assert "t(adjustment.reason" not in DEPOSIT_OPERATION
    assert "reason:reason.trim()" in DISPOSITION_OPERATION
    assert "t(reason" not in DISPOSITION_OPERATION


def test_known_system_deposit_and_platform_names_are_translated():
    localized_sources = LANGUAGE_CONTEXT + (FRONTEND / "utils" / "activityLabels.ts").read_text(encoding="utf-8")
    assert "'Monthly Deposit':'وديعة شهرية'" in localized_sources
    assert "'Wadaie':'ودائع'" in localized_sources


def test_break_deposit_header_description_and_known_option_names_are_localized():
    description = "Close a deposit and post the actual settlement received."
    assert f"description: '{description}'" in OPERATION_REGISTRY
    assert "{t(pageDescription)}" in WORKSPACE_PAGE
    assert f"'{description}':'أغلق الوديعة ورحّل مبلغ التسوية الفعلي المستلم.'" in LANGUAGE_CONTEXT
    assert "item.product_name==='Monthly Deposit'?t('Monthly Deposit'):item.product_name" in DISPOSITION_OPERATION
    assert "item.provider_name==='Wadaie'?t('Wadaie'):item.provider_name" in DISPOSITION_OPERATION
