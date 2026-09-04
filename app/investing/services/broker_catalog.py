from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher
import re


@dataclass(frozen=True)
class BrokerCatalogItem:
    name: str
    country: str
    website: str
    aliases: tuple[str, ...] = ()
    default_commission_rate: Decimal | None = None
    commission_source: str | None = None
    default_commission_tax_rate: Decimal | None = None
    commission_tax_source: str | None = None
    institution_name: str | None = None
    execution_partner: str | None = None


BROKER_CATALOG = (
    BrokerCatalogItem("Al Rajhi Tadawul", "Saudi Arabia", "https://www.alrajhi-capital.com", ("Al Rajhi Capital", "Al Rajhi", "Rajhi Capital", "الراجحي تداول", "الراجحي", "الراجحي المالية"), institution_name="Al Rajhi Capital"),
    BrokerCatalogItem("Al Rajhi Global", "Saudi Arabia", "https://www.alrajhi-capital.com", ("Rajhi Global", "AlRajhi Global", "الراجحي قلوبال", "الراجحي جلوبال", "الراجحي العالمي"), institution_name="Al Rajhi Capital", execution_partner="Interactive Brokers (IBKR)"),
    BrokerCatalogItem("AlAhli Tadawul", "Saudi Arabia", "https://www.alahlicapital.com", ("SNB Capital", "AlAhli Capital", "NCB Capital", "الأهلي تداول", "الاهلي تداول", "الأهلي المالية", "الاهلي المالية"), Decimal("0.155"), "Saudi Exchange published maximum", Decimal("15"), "Saudi Arabia standard VAT", "SNB Capital"),
    BrokerCatalogItem("AlAhli Global", "Saudi Arabia", "https://www.alahlicapital.com", ("SNB Global", "Ahli Global", "SNB International", "الأهلي قلوبال", "الاهلي قلوبال", "الأهلي جلوبال", "الاهلي جلوبال"), None, None, Decimal("15"), "Saudi Arabia standard VAT", "SNB Capital"),
    BrokerCatalogItem("Riyad Capital", "Saudi Arabia", "https://www.riyadcapital.com", ("Riyad Bank Capital", "الرياض المالية")),
    BrokerCatalogItem("Riyad Global", "Saudi Arabia", "https://www.riyadcapital.com/us-market", ("Riyad Global Trading", "Riyad Dawli", "الرياض جلوبال", "رياض قلوبال", "الرياض العالمي", "الرياض دولي")),
    BrokerCatalogItem("Derayah Financial", "Saudi Arabia", "https://www.derayah.com", ("Derayah", "دراية", "دراية المالية")),
    BrokerCatalogItem("Derayah Global", "Saudi Arabia", "https://web.derayah.com/en/platforms/derayah-global/", ("Derayah Global Trading", "دراية جلوبال", "دراية قلوبال", "درايه جلوبال", "درايه قلوبال")),
    BrokerCatalogItem("Alinma Capital", "Saudi Arabia", "https://www.alinmacapital.com", ("Alinma Investment", "الإنماء للاستثمار", "الانماء للاستثمار")),
    BrokerCatalogItem("AlJazira Capital", "Saudi Arabia", "https://www.aljaziracapital.com.sa", ("Al Jazira Capital", "الجزيرة كابيتال", "الجزيرة المالية")),
    BrokerCatalogItem("ANB Capital", "Saudi Arabia", "https://www.anbcapital.com.sa", ("Arab National Bank Capital", "العربي المالية")),
    BrokerCatalogItem("AlBilad Investment", "Saudi Arabia", "https://www.albilad-capital.com", ("AlBilad Capital", "البلاد المالية", "البلاد للاستثمار")),
    BrokerCatalogItem("SAB Invest", "Saudi Arabia", "https://www.sabinvest.com", ("SABB Invest", "SAB Capital", "ساب للاستثمار")),
    BrokerCatalogItem("BSF Capital", "Saudi Arabia", "https://www.bsfcapital.sa", ("Saudi Fransi Capital", "Fransi Capital", "السعودي الفرنسي كابيتال")),
    BrokerCatalogItem("Alistithmar Capital", "Saudi Arabia", "https://www.alistithmarcapital.com", ("Saudi Investment Bank Capital", "الاستثمار كابيتال")),
    BrokerCatalogItem("Jadwa Investment", "Saudi Arabia", "https://www.jadwa.com", ("Jadwa", "جدوى للاستثمار", "جدوى")),
    BrokerCatalogItem("GIB Capital", "Saudi Arabia", "https://www.gibcapital.com", ("Gulf International Bank Capital", "جي آي بي كابيتال")),
    BrokerCatalogItem("HSBC Saudi Arabia", "Saudi Arabia", "https://www.hsbcsaudi.com", ("HSBC Saudi", "إتش إس بي سي السعودية")),
    BrokerCatalogItem("Yaqeen Capital", "Saudi Arabia", "https://www.yaqeen.sa", ("Falcom", "يقين كابيتال")),
    BrokerCatalogItem("Awaed Capital", "Saudi Arabia", "https://www.awaed.com", ("Awaed Alosool", "عوائد", "عوائد الأصول")),
    BrokerCatalogItem("Sahm Capital", "Saudi Arabia", "https://www.sahmcapital.com", ("Sahm", "Sahm Saudi", "Sahm US", "سهم", "سهم كابيتال", "سهم السعودي", "سهم الأمريكي", "سهم الامريكي")),
    BrokerCatalogItem("Abyan Trading", "Saudi Arabia", "https://www.abyancapital.sa/trade", ("Abyan Capital", "Abyan Trade", "أبيان", "ابيان", "أبيان تداول", "ابيان تداول", "أبيان كابيتال")),
    BrokerCatalogItem("Fidelity Investments", "United States", "https://www.fidelity.com", ("Fidelity",)),
    BrokerCatalogItem("Charles Schwab", "United States", "https://www.schwab.com", ("Schwab",)),
    BrokerCatalogItem("Interactive Brokers (IBKR)", "United States", "https://www.interactivebrokers.com", ("IBKR", "Interactive Broker", "Interactive Brokers"), None, "Official variable per-share pricing; confirm the selected IBKR plan", Decimal("0"), "No VAT charged by the US broker", "Interactive Brokers"),
    BrokerCatalogItem("E*TRADE", "United States", "https://us.etrade.com", ("ETrade", "E Trade", "Morgan Stanley ETRADE")),
    BrokerCatalogItem("Robinhood", "United States", "https://www.robinhood.com", ("Robin Hood",)),
    BrokerCatalogItem("Webull", "United States", "https://www.webull.com", ("Webull Financial",)),
    BrokerCatalogItem("Vanguard", "United States", "https://investor.vanguard.com", ("The Vanguard Group",)),
    BrokerCatalogItem("Merrill Edge", "United States", "https://www.merrilledge.com", ("Merrill Lynch", "Merrill")),
    BrokerCatalogItem("TradeStation", "United States", "https://www.tradestation.com", ("Trade Station", "TradeStation Securities"), None, "Official pricing varies by residency, volume, and routing", Decimal("0"), "No VAT charged by the US broker", "TradeStation Securities"),
    BrokerCatalogItem("tastytrade", "United States", "https://www.tastytrade.com", ("Tasty Trade", "tastyworks")),
    BrokerCatalogItem("SoFi Invest", "United States", "https://www.sofi.com/invest", ("SoFi",)),
    BrokerCatalogItem("Public", "United States", "https://public.com", ("Public.com", "Public Investing")),
    BrokerCatalogItem("moomoo", "United States", "https://www.moomoo.com", ("Moomoo Financial",)),
)


def effective_commission_rate(item: BrokerCatalogItem) -> Decimal | None:
    if item.default_commission_rate is not None:
        return item.default_commission_rate
    # Saudi local-equity services use the Saudi Exchange published maximum.
    local_services = {
        "Al Rajhi Tadawul", "AlAhli Tadawul", "Riyad Capital", "Derayah Financial",
        "Alinma Capital", "AlJazira Capital", "ANB Capital", "AlBilad Investment",
        "SAB Invest", "BSF Capital", "Alistithmar Capital", "Jadwa Investment",
        "GIB Capital", "HSBC Saudi Arabia", "Yaqeen Capital", "Awaed Capital",
        "Sahm Capital", "Abyan Trading",
    }
    return Decimal("0.155") if item.name in local_services else None


def effective_commission_source(item: BrokerCatalogItem) -> str | None:
    if item.commission_source:
        return item.commission_source
    return "Saudi Exchange published maximum" if effective_commission_rate(item) is not None else None


def effective_vat_rate(item: BrokerCatalogItem) -> Decimal | None:
    if item.country == "Saudi Arabia":
        return Decimal("15")
    if item.country == "United States":
        return Decimal("0")
    return item.default_commission_tax_rate


def effective_vat_source(item: BrokerCatalogItem) -> str | None:
    if item.country == "Saudi Arabia":
        return "Saudi Arabia standard VAT"
    if item.country == "United States":
        return "No VAT charged by the US broker"
    return item.commission_tax_source


_ARABIC_MAP = str.maketrans({"أ":"ا", "إ":"ا", "آ":"ا", "ى":"ي", "ة":"ه", "ؤ":"و", "ئ":"ي"})


def normalize_broker_name(value: str) -> str:
    normalized = value.strip().lower().translate(_ARABIC_MAP)
    return re.sub(r"[^a-z0-9\u0600-\u06ff]+", "", normalized)


def broker_match(value: str) -> tuple[BrokerCatalogItem | None, bool]:
    candidate = normalize_broker_name(value)
    if not candidate:
        return None, False
    best_item = None
    best_score = 0.0
    for item in BROKER_CATALOG:
        canonical = normalize_broker_name(item.name)
        if candidate == canonical:
            return item, True
        for label in item.aliases:
            known = normalize_broker_name(label)
            if candidate == known:
                return item, False
            score = SequenceMatcher(None, candidate, known).ratio()
            if min(len(candidate), len(known)) >= 4 and (candidate in known or known in candidate):
                score = max(score, 0.9)
            if score > best_score:
                best_item, best_score = item, score
    return (best_item, False) if best_score >= 0.76 else (None, False)
