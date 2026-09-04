from app.investing.services.market_security_search import SahmkMarketSecuritySearch


def test_sahmk_directory_maps_stocks_reits_and_funds(monkeypatch):
    provider = SahmkMarketSecuritySearch("test-key")
    monkeypatch.setattr(provider, "_load", lambda url: {"results": [
        {"symbol": "2222", "name": "أرامكو", "name_en": "Saudi Arabian Oil Co", "security_type": "EQUITY"},
        {"symbol": "4348", "name_en": "Alkhabeer REIT Fund", "security_type": "REIT"},
        {"symbol": "4702", "name_en": "Alkhabeer Diversified Income 2030", "security_type": "CEF"},
    ]})
    results = provider.search("الخبير")
    assert [(item.symbol, item.security_type) for item in results] == [("2222", "STOCK"), ("4348", "REIT"), ("4702", "ETF")]
    assert all(item.currency_code == "SAR" and item.market_symbol.endswith(".SR") for item in results)
