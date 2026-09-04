from enum import Enum


class TradeType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    DIVIDEND = "DIVIDEND"
    SPLIT = "SPLIT"