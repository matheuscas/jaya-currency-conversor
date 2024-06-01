import dataclasses
from datetime import datetime
from decimal import Decimal
from typing import Protocol

import pytz  # type: ignore

from conversion.models import Conversion as ConversionModel  # type: ignore
from conversion.domain import Conversion, ConversionRequest, ConversionResponse
from django.conf import settings
from django.contrib.auth import get_user_model

from conversion.exceptions import (
    ConversionRateServiceException,
    CurrencyNotFoundException,
)


class ConversionRateServiceProtocol(Protocol):
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

    def get_latest_rates(self) -> dict:
        return {}

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


class ConversionService:
    def __init__(self, conversion_rate_service: ConversionRateServiceProtocol) -> None:
        self.conversion_rate_service = conversion_rate_service

    def convert_currency(self, request: ConversionRequest) -> ConversionResponse:
        return self.conversion_rate_service.get_conversion_from(request)


class ConversionDbService:
    def create(self, conversion: Conversion) -> Conversion:
        conversion_obj = ConversionModel.objects.create(
            user=get_user_model().objects.get(external_id=conversion.user_id),
            from_currency=conversion.request.from_currency,
            from_amount=conversion.request.amount,
            to_currency=conversion.request.to_currency,
            to_amount=conversion.response.converted_amount,
            rate=conversion.response.rate,
            created_at=conversion.response.created_at,
        )
        new_conversion: Conversion = dataclasses.replace(conversion)
        new_conversion.id = conversion_obj.id
        return new_conversion

    def listByUser(self, user_id: str) -> list[Conversion]:
        user_conversions: list[Conversion] = []
        conversions_list = ConversionModel.objects.filter(user__external_id=user_id)
        for conversion in conversions_list:
            user_conversions.append(
                Conversion(
                    id=conversion.id,
                    user_id=conversion.user_id,
                    request=ConversionRequest(
                        from_currency=conversion.from_currency,
                        amount=conversion.from_amount,
                        to_currency=conversion.to_currency,
                    ),
                    response=ConversionResponse(
                        converted_amount=conversion.to_amount,
                        rate=conversion.rate,
                        created_at=conversion.created_at,
                    ),
                )
            )
        return user_conversions
