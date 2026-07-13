from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class JournalLineInput:
    account_id: int
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")