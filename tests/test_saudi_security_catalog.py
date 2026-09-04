import pytest

from app.investing.services.saudi_security_catalog import search_saudi_catalog


@pytest.mark.parametrize("query", ["الاتصالات", "الاتصالات السعودية", "STC", "Saudi Telecom", "7010", "7010.SR"])
def test_stc_can_be_found_by_common_arabic_english_and_market_names(query):
    results = search_saudi_catalog(query)
    assert results
    assert results[0].symbol == "7010"
    assert results[0].market_symbol == "7010.SR"


@pytest.mark.parametrize("query", ["الخبير ريت", "صندوق الخبير ريت", "Alkhabeer REIT", "Al Khabeer REIT", "4348", "4348.SR"])
def test_alkhabeer_reit_can_be_found_by_arabic_english_and_symbol(query):
    results = search_saudi_catalog(query)
    assert results
    assert results[0].symbol == "4348"
    assert results[0].market_symbol == "4348.SR"
    assert results[0].security_type == "REIT"


@pytest.mark.parametrize(
    ("query", "symbol"),
    [
        ("الخبير للدخل المتنوع", "4700"),
        ("Alkhabeer Diversified Income", "4700"),
        ("4700.SR", "4700"),
        ("الخبير للدخل المتنوع 2030", "4702"),
        ("Alkhabeer Income 2030", "4702"),
        ("4702", "4702"),
    ],
)
def test_alkhabeer_listed_income_funds_can_be_found(query, symbol):
    assert any(item.symbol == symbol for item in search_saudi_catalog(query))


def test_generic_alkhabeer_search_returns_all_current_listed_funds():
    assert {item.symbol for item in search_saudi_catalog("الخبير")} == {"4348", "4700", "4701", "4702"}


@pytest.mark.parametrize(
    ("query", "symbol"),
    [
        ("بنك الإنماء", "1150"),
        ("الانماء", "1150"),
        ("Alinma", "1150"),
        ("النهدي", "4164"),
        ("Nahdi", "4164"),
        ("سال", "4263"),
        ("SAL", "4263"),
        ("أسمنت الجوف", "3091"),
        ("Jouf Cement", "3091"),
    ],
)
def test_complete_offline_catalog_finds_common_saudi_names(query, symbol):
    results = search_saudi_catalog(query)
    assert results
    assert results[0].symbol == symbol


def test_saudi_reits_and_etfs_keep_their_investment_classification():
    assert search_saudi_catalog("الرياض ريت")[0].security_type == "REIT"
    assert search_saudi_catalog("صندوق البلاد الأمريكي")[0].security_type == "ETF"


def test_saudi_security_keeps_both_display_languages_while_searching_all_aliases():
    item = search_saudi_catalog("BJAZ")[0]
    assert item.symbol == "1020"
    assert item.name_ar == "بنك الجزيرة"
    assert item.name_en == "Bank AlJazira"
    assert search_saudi_catalog("بنك الجزيرة")[0].symbol == "1020"


def test_bank_and_masraf_terms_find_companies_by_their_full_commercial_names():
    bank_symbols = {item.symbol for item in search_saudi_catalog("بنك")}
    masraf_symbols = {item.symbol for item in search_saudi_catalog("مصرف")}
    assert {"1010", "1020", "1140"}.issubset(bank_symbols)
    assert {"1120", "1150"}.issubset(masraf_symbols)
