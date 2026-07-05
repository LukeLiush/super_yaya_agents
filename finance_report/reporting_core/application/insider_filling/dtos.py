from datetime import date
from decimal import Decimal
from ...domain.shared_values import ValueObject

class InsiderTransaction(ValueObject):
    insider_name: str
    insider_title: str
    transaction_date: date
    code: str  # "P" purchase, "S" sale, ...
    shares: int
    price: Decimal
    transaction_type: str
