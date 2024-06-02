import dataclasses
import datetime
from decimal import Decimal
from typing import Any, Protocol

import pytz  # type: ignore
import requests  # type: ignore

from conversion.models import Conversion as ConversionModel  # type: ignore
from conversion.domain import Conversion, ConversionRequest, ConversionResponse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache

from conversion.exceptions import (
    ConversionRateServiceException,
    CurrencyNotFoundException,
)

import structlog

logger = structlog.get_logger(__name__)


class ConversionRatesProtocol(Protocol):
    def __init__(self, cache: "ConversionRatesCacheService") -> None: ...
    def get_conversion_from(self, request: ConversionRequest) -> ConversionResponse: ...


class ExchangeRatesAPI:
    def __init__(self, cache_service: "ConversionRatesCacheService") -> None:
        self.cache_service = cache_service

    # By default it uses EUR as base
    url = f"http://api.exchangeratesapi.io/v1/latest?access_key={settings.EXCHANGE_API_KEY}"

    def get_conversion_from(self, request: ConversionRequest) -> ConversionResponse:
        response = self.get_latest_rates()
        if response["success"]:
            if (
                request.from_currency not in response["rates"]
                or request.to_currency not in response["rates"]
            ):
                logger.exception(
                    "Currency not found",
                    from_currency=request.from_currency,
                    to_currency=request.to_currency,
                )
                raise CurrencyNotFoundException(
                    f"{request.from_currency} or {request.to_currency} not found"
                )
            logger.info("Conversion success", **dataclasses.asdict(request))
            return self.convert_amount(request, response)
        else:
            logger.exception(
                "Api internal error",
                code=response["error"]["code"],
                info=response["error"]["info"],
            )
            raise ConversionRateServiceException(
                f"{response['error']['code']}: {response['error']['info']}"
            )

    def parse_timestamp_to_datetime(self, timestamp: int) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(timestamp, pytz.UTC)

    def get_latest_rates(self) -> dict:
        data_in_cache = self.cache_service.get_rates(self.todays_key)
        if data_in_cache:
            logger.info("Rates from cache")
            return data_in_cache
        else:
            logger.info("Rates from API")
            response = requests.get(self.url)
            data = response.json()
            self.cache_service.save_rates(self.todays_key, data)
            return data

    @property
    def todays_key(self) -> str:
        today = datetime.datetime.now(tz=pytz.UTC)
        return f"{today:%Y-%m-%d}"

    def convert_amount(
        self, request: ConversionRequest, rates: dict
    ) -> ConversionResponse:
        rates_timestamp = self.parse_timestamp_to_datetime(rates["timestamp"])
        now = datetime.datetime.now(tz=pytz.UTC)
        if request.from_currency == rates["base"]:
            rate = rates["rates"][request.to_currency]
            return ConversionResponse(
                rate=rate,
                rates_timestamp=rates_timestamp,
                converted_amount=Decimal(request.amount)
                * Decimal(rates["rates"][request.to_currency]),
                created_at=now,
            )
        elif request.to_currency == rates["base"]:
            rate = Decimal(1) / Decimal(rates["rates"][request.from_currency])
            return ConversionResponse(
                rate=rate,
                rates_timestamp=rates_timestamp,
                converted_amount=Decimal(request.amount) * rate,
                created_at=now,
            )
        else:
            from_currency_rate = Decimal(rates["rates"][request.from_currency])
            to_currency_rate = Decimal(rates["rates"][request.to_currency])
            final_rate = to_currency_rate / from_currency_rate
            return ConversionResponse(
                rate=final_rate,
                rates_timestamp=rates_timestamp,
                converted_amount=Decimal(request.amount) * final_rate,
                created_at=now,
            )


class ConversionService:
    def __init__(self, conversion_rate_service: ConversionRatesProtocol) -> None:
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
            rates_timestamp=conversion.response.rates_timestamp,
        )
        new_conversion: Conversion = dataclasses.replace(conversion)
        new_conversion.id = conversion_obj.id
        new_conversion.response.created_at = conversion_obj.created_at
        return new_conversion

    def listByUser(self, user_id: str) -> list[Conversion]:
        user_conversions: list[Conversion] = []
        conversions_list = ConversionModel.objects.filter(user__external_id=user_id)
        for conversion in conversions_list:
            user_conversions.append(
                Conversion(
                    id=conversion.id,
                    user_id=conversion.user.external_id,
                    request=ConversionRequest(
                        from_currency=conversion.from_currency,
                        amount=conversion.from_amount,
                        to_currency=conversion.to_currency,
                    ),
                    response=ConversionResponse(
                        converted_amount=conversion.to_amount,
                        rate=conversion.rate,
                        rates_timestamp=conversion.rates_timestamp,
                        created_at=conversion.created_at,
                    ),
                )
            )
        return user_conversions


class CacheProtocol(Protocol):
    def set(self, key, value, timeout=300, version=None) -> None: ...
    def get(self, key, default=None, version=None) -> Any: ...


class MidnightCache:
    """ "
    MidnightCache is a cache object that automatically expires at midnight.
    It provides a convenient way to store data that should expire at the end of the day.
    It is based on Django's cache object.
    """

    def set(self, key, value, timeout=86400, version=None) -> None:
        """
        This method sets a value in the cache with a specific key, a timeout (default is 24 hours), and an optional version.
        The timeout is overwritten by the number of seconds until midnight.
        The timeout argument is kept for backwards compatibility.
        """
        cache.set(
            key, value, timeout=self.calculate_seconds_until_midnight(), version=version
        )

    def get(self, key, default=None, version=None) -> Any:
        return cache.get(key, default=default, version=version)

    def calculate_seconds_until_midnight(self) -> int:
        now = datetime.datetime.now()
        midnight = datetime.datetime.combine(
            now.date(), datetime.time()
        ) + datetime.timedelta(days=1)
        time_left = (midnight - now).total_seconds()
        return int(time_left)  # one second less or more is irrelevant


class ConversionRatesCacheService:
    def __init__(self, cache: CacheProtocol) -> None:
        self.cache = cache

    def get_rates(self, key, default=None, version=None) -> Any:
        return self.cache.get(key, default=default, version=version)

    def save_rates(self, key, value, timeout=300, version=None) -> None:
        self.cache.set(key, value, timeout=timeout, version=version)
