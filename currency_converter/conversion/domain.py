from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class ConversionRequest:
    from_currency: str
    to_currency: str
    amount: Decimal


@dataclass
class ConversionResponse:
    rate: Decimal
    rates_timestamp: datetime
    converted_amount: Decimal


@dataclass
class Conversion:
    user_id: str
    request: ConversionRequest
    response: ConversionResponse
    id: Optional[str] = None
