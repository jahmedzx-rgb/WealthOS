from enum import Enum


class AssetType(str, Enum):
    STOCK = "STOCK"
    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    BOND = "BOND"
    REIT = "REIT"
    CRYPTO = "CRYPTO"
    CASH = "CASH"