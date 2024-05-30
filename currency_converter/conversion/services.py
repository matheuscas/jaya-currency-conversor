from datetime import datetime
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
        if request.from_currency == request.to_currency:
            return ConversionResponse(
                rate=1, created_at=datetime.now(), converted_amount=request.amount
            )
        else:
            response = self.get_latest_rates()
            if (
                request.from_currency not in response["rates"]
                or request.to_currency not in response["rates"]
            ):
                raise CurrencyNotFoundException(
                    f"{request.from_currency} or {request.to_currency} not found"
                )
            if response["success"]:
                return ConversionResponse(
                    rate=response["rates"][request.to_currency],
                    created_at=self.get_datetime_from_timestamp(response["timestamp"]),
                    converted_amount=request.amount
                    * response["rates"][request.to_currency],
                )
            else:
                raise ConversionRateServiceException(
                    f"{response['error']['code']}: {response['error']['info']}"
                )

    def get_datetime_from_timestamp(self, timestamp: int) -> datetime:
        return datetime.fromtimestamp(timestamp, pytz.UTC)

    def get_latest_rates(self) -> dict: ...
