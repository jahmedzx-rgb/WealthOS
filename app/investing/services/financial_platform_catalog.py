from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FinancialPlatform:
    code: str
    name: str
    name_ar: str
    country: str
    website: str
    services: tuple[str, ...]
    description: str


FINANCIAL_PLATFORMS = (
    FinancialPlatform("AFAQ", "Afaq Capital", "آفاق المالية", "Saudi Arabia", "https://afaq.co/ar", ("EQUITY_CROWDFUNDING", "PRIVATE_EQUITY", "PRIVATE_FUND", "PRIVATE_SUKUK", "MANAGED_PORTFOLIO"), "Private equity, private funds, sukuk, and managed portfolios."),
    FinancialPlatform("TAMRA", "Tamra Capital", "تمرة المالية", "Saudi Arabia", "https://tamracapital.sa", ("ROBO_ADVISOR", "MANAGED_PORTFOLIO"), "Automated diversified investment portfolios."),
    FinancialPlatform("MALAA", "Malaa", "ملاءة", "Saudi Arabia", "https://malaa.tech", ("ROBO_ADVISOR", "MANAGED_PORTFOLIO"), "Digital wealth and managed investment portfolios."),
    FinancialPlatform("ABYAN", "Abyan Capital", "أبيان المالية", "Saudi Arabia", "https://abyancapital.sa", ("MANAGED_PORTFOLIO", "BROKERAGE"), "Managed portfolios and investment services."),
    FinancialPlatform("TARMEEZ", "Tarmeez Capital", "ترميز المالية", "Saudi Arabia", "https://tarmeez.co", ("PRIVATE_SUKUK", "DEBT_CROWDFUNDING"), "Private sukuk and debt investment opportunities."),
    FinancialPlatform("SAFQAH", "Safqah Capital", "صفقة المالية", "Saudi Arabia", "https://safqah.co", ("REAL_ESTATE_CROWDFUNDING", "ALTERNATIVE_INVESTMENTS"), "Alternative and fractional investment opportunities."),
    FinancialPlatform("STAKE", "Stake", "ستيك", "Saudi Arabia / UAE", "https://getstake.com/ar/ksa", ("REAL_ESTATE_CROWDFUNDING", "REAL_ESTATE_FUNDS"), "Fractional and fund-based real estate investing."),
    FinancialPlatform("MANAFA", "Manafa", "منافع", "Saudi Arabia", "https://manafa.sa", ("DEBT_CROWDFUNDING", "EQUITY_CROWDFUNDING"), "Debt and equity crowdfunding opportunities."),
    FinancialPlatform("SUKUK", "Sukuk Capital", "صكوك المالية", "Saudi Arabia", "https://sukuk.sa", ("PRIVATE_SUKUK", "DEBT_CROWDFUNDING"), "Sukuk and debt investment opportunities."),
    FinancialPlatform("HAKBAH", "Hakbah", "هكبه", "Saudi Arabia", "https://hakbah.sa", ("SAVING_CIRCLES",), "Digital saving circles."),
    FinancialPlatform("CIRCLES", "Circlys", "سيركليز", "Saudi Arabia", "https://www.circlys.com", ("SAVING_CIRCLES",), "Digital saving circles."),
    FinancialPlatform("DINAR", "Dinar Investment", "دينار المالية", "Saudi Arabia", "https://www.dinar.sa", ("PRIVATE_SUKUK", "DEBT_CROWDFUNDING", "MANAGED_PORTFOLIO"), "Sharia-compliant sukuk, funds, savings, and managed investment products."),
)


def platform_catalog() -> list[dict]:
    return [{**asdict(item), "services": list(item.services)} for item in FINANCIAL_PLATFORMS]
