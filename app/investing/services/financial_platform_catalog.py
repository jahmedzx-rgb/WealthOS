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
    FinancialPlatform("TAMRA", "Tamra Capital", "تمرة المالية", "Saudi Arabia", "https://tamracapital.sa", ("ROBO_ADVISOR", "MANAGED_PORTFOLIO"), "Automated diversified investment portfolios."),
    FinancialPlatform("MALAA", "Malaa", "ملاءة", "Saudi Arabia", "https://malaa.tech", ("ROBO_ADVISOR", "MANAGED_PORTFOLIO"), "Digital wealth and managed investment portfolios."),
    FinancialPlatform("ABYAN", "Abyan Capital", "أبيان المالية", "Saudi Arabia", "https://abyancapital.sa", ("MANAGED_PORTFOLIO", "BROKERAGE"), "Managed portfolios and investment services."),
    FinancialPlatform("TARMEEZ", "Tarmeez Capital", "ترميز المالية", "Saudi Arabia", "https://tarmeez.co", ("PRIVATE_SUKUK", "DEBT_CROWDFUNDING"), "Private sukuk and debt investment opportunities."),
    FinancialPlatform("SAFQAH", "Safqah Capital", "صفقة المالية", "Saudi Arabia", "https://safqah.sa", ("REAL_ESTATE_CROWDFUNDING", "ALTERNATIVE_INVESTMENTS"), "Alternative and fractional investment opportunities."),
    FinancialPlatform("STAKE", "Stake", "ستيك", "Saudi Arabia / UAE", "https://getstake.com", ("REAL_ESTATE_CROWDFUNDING", "REAL_ESTATE_FUNDS"), "Fractional and fund-based real estate investing."),
    FinancialPlatform("MANAFA", "Manafa", "منافع", "Saudi Arabia", "https://manafa.co", ("DEBT_CROWDFUNDING", "EQUITY_CROWDFUNDING"), "Debt and equity crowdfunding opportunities."),
    FinancialPlatform("FORUS", "Forus", "فرص", "Saudi Arabia", "https://forus.com", ("DEBT_CROWDFUNDING",), "Debt crowdfunding opportunities."),
    FinancialPlatform("SUKUK", "Sukuk Capital", "صكوك المالية", "Saudi Arabia", "https://sukuk.sa", ("PRIVATE_SUKUK", "DEBT_CROWDFUNDING"), "Sukuk and debt investment opportunities."),
    FinancialPlatform("HAKBAH", "Hakbah", "هكبه", "Saudi Arabia", "https://hakbah.sa", ("SAVING_CIRCLES",), "Digital saving circles."),
    FinancialPlatform("CIRCLES", "Saving Circles", "جمعيات الادخار", "Saudi Arabia", "", ("SAVING_CIRCLES",), "Manual or provider-based saving circles."),
)


def platform_catalog() -> list[dict]:
    return [{**asdict(item), "services": list(item.services)} for item in FINANCIAL_PLATFORMS]

