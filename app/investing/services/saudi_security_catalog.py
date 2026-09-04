from dataclasses import dataclass
import json
from pathlib import Path
import re


@dataclass(frozen=True)
class SaudiSecurityCatalogItem:
    symbol: str
    name: str
    security_type: str
    aliases: tuple[str, ...]
    name_ar: str | None = None
    name_en: str | None = None

    @property
    def market_symbol(self) -> str:
        return f"{self.symbol}.SR"


CURATED_SAUDI_SECURITY_CATALOG = (
    SaudiSecurityCatalogItem(
        symbol="4348",
        name="Alkhabeer REIT Fund",
        security_type="REIT",
        aliases=(
            "Alkhabeer REIT",
            "Al Khabeer REIT",
            "Alkhabir REIT",
            "Khabeer REIT",
            "الخبير ريت",
            "صندوق الخبير ريت",
            "الخبير العقاري",
            "صندوق الخبير العقاري",
        ),
    ),
    SaudiSecurityCatalogItem(
        symbol="4700",
        name="Alkhabeer Diversified Income Traded Fund",
        security_type="ETF",
        aliases=(
            "Alkhabeer Diversified Income",
            "Al Khabeer Diversified Income Fund",
            "Alkhabeer Income Fund",
            "الخبير للدخل المتنوع المتداول",
            "صندوق الخبير للدخل المتنوع المتداول",
            "الخبير للدخل المتنوع",
            "صندوق الخبير للدخل المتنوع",
        ),
    ),
    SaudiSecurityCatalogItem(
        symbol="4702",
        name="Alkhabeer Diversified Income Traded Fund 2030",
        security_type="ETF",
        aliases=(
            "Alkhabeer Diversified Income 2030",
            "Al Khabeer Diversified Income Fund 2030",
            "Alkhabeer Income 2030",
            "الخبير للدخل المتنوع 2030 المتداول",
            "صندوق الخبير للدخل المتنوع 2030 المتداول",
            "الخبير 2030",
            "صندوق الخبير 2030",
        ),
    ),
    SaudiSecurityCatalogItem(
        symbol="7010",
        name="Saudi Telecom Company (stc)",
        security_type="STOCK",
        aliases=(
            "STC",
            "Saudi Telecom",
            "Saudi Telecom Company",
            "الاتصالات",
            "الاتصالات السعودية",
            "شركة الاتصالات السعودية",
            "اس تي سي",
        ),
    ),
)


def _load_offline_catalog() -> tuple[SaudiSecurityCatalogItem, ...]:
    path = Path(__file__).resolve().parents[1] / "data" / "saudi_securities.json"
    if not path.exists():
        return CURATED_SAUDI_SECURITY_CATALOG
    records = json.loads(path.read_text(encoding="utf-8"))
    curated = {item.symbol: item for item in CURATED_SAUDI_SECURITY_CATALOG}
    full_english_names = {
        "1010": "Riyad Bank", "1020": "Bank AlJazira", "1030": "Saudi Investment Bank",
        "1050": "Banque Saudi Fransi", "1060": "Saudi Awwal Bank", "1080": "Arab National Bank",
        "1120": "Al Rajhi Bank", "1140": "Bank Albilad", "1150": "Alinma Bank", "1180": "Saudi National Bank",
    }
    full_arabic_names = {
        "1010": "بنك الرياض", "1020": "بنك الجزيرة", "1030": "البنك السعودي للاستثمار",
        "1050": "البنك السعودي الفرنسي", "1060": "البنك السعودي الأول", "1080": "البنك العربي الوطني",
        "1120": "مصرف الراجحي", "1140": "بنك البلاد", "1150": "مصرف الإنماء", "1180": "البنك الأهلي السعودي",
    }
    items = list(CURATED_SAUDI_SECURITY_CATALOG)
    for record in records:
        symbol = str(record.get("symbol", "")).strip()
        name_ar = str(record.get("name_ar") or "").strip()
        raw_name_ar = name_ar
        name_ar = full_arabic_names.get(symbol, name_ar)
        raw_name_en = str(record.get("name_en") or symbol).strip()
        name_en = full_english_names.get(symbol, raw_name_en)
        if not symbol:
            continue
        raw_type = str(record.get("security_type") or "STOCK").upper()
        if not any(value in raw_type for value in ("EQUITY", "ETF", "FUND", "CEF")):
            continue
        security_type = "REIT" if "REIT" in raw_type or "REIT" in name_en.upper() or "ريت" in name_ar else "ETF" if any(value in raw_type for value in ("ETF", "FUND", "CEF")) else "STOCK"
        if symbol in curated:
            item = curated[symbol]
            index = items.index(item)
            items[index] = SaudiSecurityCatalogItem(item.symbol, name_ar or item.name, item.security_type, tuple(dict.fromkeys((*item.aliases, item.name, raw_name_ar, name_ar, raw_name_en, name_en))), name_ar or None, name_en or item.name)
        else:
            items.append(SaudiSecurityCatalogItem(symbol, name_ar or name_en, security_type, tuple(value for value in (raw_name_ar, name_ar, raw_name_en, name_en) if value), name_ar or None, name_en or None))
    return tuple(items)


SAUDI_SECURITY_CATALOG = _load_offline_catalog()


_ARABIC_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})


def normalize_security_query(value: str) -> str:
    normalized = value.strip().lower().translate(_ARABIC_MAP)
    return re.sub(r"[^a-z0-9\u0600-\u06ff]+", "", normalized)


def search_saudi_catalog(query: str) -> list[SaudiSecurityCatalogItem]:
    candidate = normalize_security_query(query)
    if len(candidate) < 2:
        return []
    matches: list[tuple[int, SaudiSecurityCatalogItem]] = []
    for item in SAUDI_SECURITY_CATALOG:
        labels = (item.symbol, item.market_symbol, item.name, *item.aliases)
        normalized_labels = [normalize_security_query(label) for label in labels if label]
        scores = [0 if label == candidate else 1 if label.startswith(candidate) else 2 if candidate in label else 3 for label in normalized_labels if candidate in label or label in candidate]
        if scores:
            matches.append((min(scores), item))
    return [item for _, item in sorted(matches, key=lambda match: (match[0], match[1].symbol))]
