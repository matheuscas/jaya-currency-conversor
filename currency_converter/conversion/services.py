from datetime import datetime
from decimal import Decimal
from typing import Protocol

import pytz

from conversion.domain import ConversionRequest, ConversionResponse
from django.conf import settings

from conversion.exceptions import (
    ConversionRateServiceException,
    CurrencyNotFoundException,
)


class ConversionRateService(Protocol):
    def get_conversion_from(self, request: ConversionRequest) -> ConversionResponse: ...


class ExchangeRateService:
    # By default it uses EUR as base
    url = f"http://api.exchangeratesapi.io/v1/latest?access_key={settings.EXCHANGE_API_KEY}"

    def get_conversion_from(self, request: ConversionRequest) -> ConversionResponse:
        response = self.get_latest_rates()
        if response["success"]:
            if (
                request.from_currency not in response["rates"]
                or request.to_currency not in response["rates"]
            ):
                raise CurrencyNotFoundException(
                    f"{request.from_currency} or {request.to_currency} not found"
                )
            return self.convert_amount(request, response)
        else:
            raise ConversionRateServiceException(
                f"{response['error']['code']}: {response['error']['info']}"
            )

    def parse_timestamp_to_datetime(self, timestamp: int) -> datetime:
        return datetime.fromtimestamp(timestamp, pytz.UTC)

    def get_latest_rates(self) -> dict: ...

    def convert_amount(
        self, request: ConversionRequest, rates: dict
    ) -> ConversionResponse:
        created_at = self.parse_timestamp_to_datetime(rates["timestamp"])
        if request.from_currency == rates["base"]:
            rate = rates["rates"][request.to_currency]
            return ConversionResponse(
                rate=rate,
                created_at=created_at,
                converted_amount=Decimal(request.amount)
                * Decimal(rates["rates"][request.to_currency]),
            )
        elif request.to_currency == rates["base"]:
            rate = Decimal(1) / Decimal(rates["rates"][request.from_currency])
            return ConversionResponse(
                rate=rate,
                created_at=created_at,
                converted_amount=Decimal(request.amount) * rate,
            )
        else:
            from_currency_rate = Decimal(rates["rates"][request.from_currency])
            to_currency_rate = Decimal(rates["rates"][request.to_currency])
            final_rate = to_currency_rate / from_currency_rate
            return ConversionResponse(
                rate=final_rate,
                created_at=created_at,
                converted_amount=Decimal(request.amount) * final_rate,
            )
