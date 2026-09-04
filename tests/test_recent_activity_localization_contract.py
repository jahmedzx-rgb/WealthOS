from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"
ACTIVITY_LABELS = (FRONTEND / "utils" / "activityLabels.ts").read_text(encoding="utf-8")
RECENT_ACTIVITY = (FRONTEND / "components" / "dashboard" / "RecentActivity.tsx").read_text(encoding="utf-8")
ACTIVITY_PAGE = (FRONTEND / "pages" / "RecentActivityPage.tsx").read_text(encoding="utf-8")
LANGUAGE_CONTEXT = (FRONTEND / "context" / "LanguageContext.tsx").read_text(encoding="utf-8")


SYSTEM_ACTIVITY_COPY = {
    "Security Purchase", "Security Sale",
    "Portfolio Funding", "Portfolio Withdrawal", "Property Sale",
    "Property Valuation Adjustment", "Property", "Deposit Closure",
    "Deposit Balance Adjustment", "Deposit", "Credit Card Payment",
    "Credit Card Balance Adjustment", "Credit Card", "Bank Account",
    "Investment Trade", "Opening Balance", "Posted Operation",
}


def test_activity_helpers_receive_the_active_language_at_both_render_sites():
    """Dashboard and full timeline must use the same locale-aware formatter."""
    for source in (RECENT_ACTIVITY, ACTIVITY_PAGE):
        assert "activityTitle(" in source
        assert "activityDetail(" in source
        assert "activityTitle(activity,language)" in source or "activityTitle(item,language)" in source
        assert "activityDetail(activity,language)" in source or "activityDetail(item,language)" in source


def test_system_generated_activity_copy_has_arabic_translation_keys():
    localized_sources = LANGUAGE_CONTEXT + ACTIVITY_LABELS
    missing = sorted(key for key in SYSTEM_ACTIVITY_COPY if f"'{key}'" not in localized_sources)
    assert missing == []


def test_activity_formatter_translates_templates_without_translating_user_values():
    """Entity names/reasons are user data; only known system fragments may pass through t()."""
    assert "return t(activity.description)" not in ACTIVITY_LABELS
    assert ".match(" in ACTIVITY_LABELS
    for fragment in ("Buy", "Sell", "Units", "Deposit funded", "Deposit broken", "Deposit balance adjustment"):
        assert fragment in ACTIVITY_LABELS
    assert "return exact[value]??value" in ACTIVITY_LABELS
    assert "systemNames[clean]??freeText(clean)" in ACTIVITY_LABELS
    # Captured product/entity names and free-form reasons pass through direction isolation only.
    assert "freeText(match[2])" in ACTIVITY_LABELS


def test_unknown_deposit_and_property_names_use_the_user_text_fallback():
    """Names outside the explicit system-name registry remain user data."""
    # Unknown entity names must continue through the exact fallback unchanged.
    assert "systemNames[clean]??freeText(clean)" in ACTIVITY_LABELS
    assert "function freeText(value:string)" in ACTIVITY_LABELS


def test_only_the_known_system_reit_name_has_an_explicit_arabic_alias():
    assert "'Alkhabeer REIT Fund':'صندوق الخبير ريت'" in ACTIVITY_LABELS
    assert "'Alkhabeer REIT':'صندوق الخبير ريت'" in ACTIVITY_LABELS


def test_wadaie_is_a_known_system_platform_name():
    assert "'Wadaie':'ودائع'" in ACTIVITY_LABELS or "'Wadaie':'ودائع'" in LANGUAGE_CONTEXT


def test_monthly_deposit_is_a_known_system_product_name():
    assert "'Monthly Deposit':'وديعة شهرية'" in ACTIVITY_LABELS or "'Monthly Deposit':'وديعة شهرية'" in LANGUAGE_CONTEXT


def test_deposit_templates_are_localized_separately_from_the_captured_names():
    assert "^Deposit funded" in ACTIVITY_LABELS
    assert "تمويل وديعة" in ACTIVITY_LABELS
    assert "^Deposit broken" in ACTIVITY_LABELS
    assert "فك وديعة" in ACTIVITY_LABELS
    assert "^Deposit balance adjustment" in ACTIVITY_LABELS
    assert "تسوية رصيد وديعة" in ACTIVITY_LABELS
    # The captured product/provider/reason values are interpolated, not translated wholesale.
    assert "freeText(match[1])" in ACTIVITY_LABELS
    assert "freeText(match[2])" in ACTIVITY_LABELS


def test_recent_activity_empty_states_are_localized_system_copy():
    for source in (RECENT_ACTIVITY, ACTIVITY_PAGE):
        assert ">No Posted Activity" not in source
        assert ">Completed operations will appear here.<" not in source
        assert "t('Completed operations will appear here.')" in source
