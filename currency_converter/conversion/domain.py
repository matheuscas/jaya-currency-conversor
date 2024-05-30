from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class ConversionRequest:
    from_currency: str
    to_currency: str
    amount: Decimal


@dataclass
class ConversionResponse:
    rate: Decimal
    created_at: datetime
    converted_amount: Decimal


@dataclass
class Conversion:
    id: str
    user_id: str
    request: ConversionRequest
    response: ConversionResponse
