# Create your tests here.
from decimal import Decimal
from freezegun import freeze_time
import pytest
import datetime
from unittest.mock import patch

from conversion.domain import Conversion, ConversionRequest, ConversionResponse
from conversion.exceptions import (
    ConversionRateServiceException,
    CurrencyNotFoundException,
)
from conversion.services import (
    ConversionDbService,
    ExchangeRateService,
    MidnightCache,
    requests,
)
from conversion.models import Conversion as ConversionModel  # type: ignore


MOCK_EXCHANGE_RATES = {
    "success": True,
    "timestamp": 1717093744,
    "base": "EUR",
    "date": "2024-05-30",
    "rates": {
        "AED": 3.981243,
        "AFN": 76.960449,
        "ALL": 101.295023,
        "AMD": 420.920088,
        "ANG": 1.953622,
        "AOA": 927.321394,
        "ARS": 969.599151,
        "AUD": 1.632531,
        "AWG": 1.953823,
        "AZN": 1.837217,
        "BAM": 1.959835,
        "BBD": 2.188706,
        "BDT": 127.261995,
        "BGN": 1.955476,
        "BHD": 0.408578,
        "BIF": 3121.780422,
        "BMD": 1.083952,
        "BND": 1.464715,
        "BOB": 7.490421,
        "BRL": 5.640447,
        "BSD": 1.083931,
        "BTC": 1.5632587e-05,
        "BTN": 90.275851,
        "BWP": 14.828528,
        "BYN": 3.546902,
        "BYR": 21245.450096,
        "BZD": 2.184998,
        "CAD": 1.482082,
        "CDF": 3062.16276,
        "CHF": 0.979783,
        "CLF": 0.036017,
        "CLP": 993.821375,
        "CNY": 7.841296,
        "CNH": 7.862058,
        "COP": 4192.995527,
        "CRC": 564.662473,
        "CUC": 1.083952,
        "CUP": 28.724716,
        "CVE": 110.806941,
        "CZK": 24.722734,
        "DJF": 192.639714,
        "DKK": 7.459299,
        "DOP": 64.224645,
        "DZD": 145.940023,
        "EGP": 51.215082,
        "ERN": 16.259273,
        "ETB": 62.16461,
        "EUR": 1,
        "FJD": 2.447022,
        "FKP": 0.862933,
        "GBP": 0.851043,
        "GEL": 3.029643,
        "GGP": 0.862933,
        "GHS": 15.988137,
        "GIP": 0.862933,
        "GMD": 73.43786,
        "GNF": 9321.983614,
        "GTQ": 8.421882,
        "GYD": 226.907135,
        "HKD": 8.472902,
        "HNL": 26.88209,
        "HRK": 7.565934,
        "HTG": 143.946343,
        "HUF": 389.391174,
        "IDR": 17572.100935,
        "ILS": 4.015542,
        "IMP": 0.862933,
        "INR": 90.298368,
        "IQD": 1419.976511,
        "IRR": 45756.299303,
        "ISK": 148.706993,
        "JEP": 0.862933,
        "JMD": 168.907731,
        "JOD": 0.768412,
        "JPY": 169.979316,
        "KES": 140.913794,
        "KGS": 95.058149,
        "KHR": 4436.613688,
        "KMF": 492.384878,
        "KPW": 975.556054,
        "KRW": 1490.909792,
        "KWD": 0.332578,
        "KYD": 0.90336,
        "KZT": 483.127989,
        "LAK": 23299.538304,
        "LBP": 97067.859742,
        "LKR": 327.203615,
        "LRD": 210.28696,
        "LSL": 20.010713,
        "LTL": 3.200627,
        "LVL": 0.655672,
        "LYD": 5.262606,
        "MAD": 10.803203,
        "MDL": 19.19151,
        "MGA": 4812.744941,
        "MKD": 61.708451,
        "MMK": 2276.386406,
        "MNT": 3739.632552,
        "MOP": 8.728169,
        "MRU": 42.870051,
        "MUR": 50.117297,
        "MVR": 16.747207,
        "MWK": 1877.948162,
        "MXN": 18.370854,
        "MYR": 5.098929,
        "MZN": 68.827174,
        "NAD": 19.944673,
        "NGN": 1566.309596,
        "NIO": 39.845753,
        "NOK": 11.423537,
        "NPR": 144.441362,
        "NZD": 1.770218,
        "OMR": 0.41727,
        "PAB": 1.083931,
        "PEN": 4.07837,
        "PGK": 4.215523,
        "PHP": 63.332579,
        "PKR": 301.826461,
        "PLN": 4.280681,
        "PYG": 8178.837807,
        "QAR": 3.946938,
        "RON": 4.976965,
        "RSD": 117.13396,
        "RUB": 97.100314,
        "RWF": 1410.220948,
        "SAR": 4.065624,
        "SBD": 9.18669,
        "SCR": 15.636008,
        "SDG": 651.454772,
        "SEK": 11.48561,
        "SGD": 1.462939,
        "SHP": 1.369519,
        "SLE": 24.765369,
        "SLL": 22729.922742,
        "SOS": 618.936787,
        "SRD": 34.839834,
        "STD": 22435.608295,
        "SVC": 9.484526,
        "SYP": 2723.460595,
        "SZL": 19.940455,
        "THB": 39.776707,
        "TJS": 11.625734,
        "TMT": 3.80467,
        "TND": 3.378707,
        "TOP": 2.560348,
        "TRY": 34.886006,
        "TTD": 7.356144,
        "TWD": 35.078817,
        "TZS": 2818.274228,
        "UAH": 43.913605,
        "UGX": 4140.524114,
        "USD": 1.083952,
        "UYU": 41.786025,
        "UZS": 13717.406287,
        "VEF": 3926671.382088,
        "VES": 39.527147,
        "VND": 27597.406094,
        "VUV": 128.688883,
        "WST": 3.038417,
        "XAF": 657.310207,
        "XAG": 0.034723,
        "XAU": 0.000463,
        "XCD": 2.929433,
        "XDR": 0.819086,
        "XOF": 655.231102,
        "XPF": 119.331742,
        "YER": 271.44856,
        "ZAR": 20.272171,
        "ZMK": 9756.875318,
        "ZMW": 29.457645,
        "ZWL": 349.031952,
    },
}

MOCK_ERROR_EXCHANGE_RATES = {
    "success": False,
    "error": {
        "code": 105,
        "info": "Rate limit exceeded",
    },
}


class MockedConversionRateCacheService:
    def get_rates(self, *args, **kwargs):
        return None

    def save_rates(self, *args, **kwargs):
        pass


class TestExchangeRateService:
    @patch.object(
        ExchangeRateService, "get_latest_rates", return_value=MOCK_EXCHANGE_RATES
    )
    def test_currency_not_found_expect_exception(self, mocked_get_latest_rates):
        service = ExchangeRateService(MockedConversionRateCacheService())
        conversion_request = ConversionRequest(
            from_currency="INVALID", to_currency="USD", amount=Decimal(100.0)
        )
        with pytest.raises(CurrencyNotFoundException):
            service.get_conversion_from(request=conversion_request)

    @patch.object(
        ExchangeRateService, "get_latest_rates", return_value=MOCK_EXCHANGE_RATES
    )
    def test_both_currencies_are_the_same_but_invalid_expect_exception(
        self,
        mocked_get_latest_rates,
    ):
        service = ExchangeRateService(MockedConversionRateCacheService())
        conversion_request = ConversionRequest(
            from_currency="INVALID", to_currency="INVALID", amount=Decimal(100.0)
        )
        with pytest.raises(CurrencyNotFoundException):
            service.get_conversion_from(request=conversion_request)

    @patch.object(
        ExchangeRateService, "get_latest_rates", return_value=MOCK_EXCHANGE_RATES
    )
    def test_both_currencies_are_the_same_expect_rate_of_1(
        self, mocked_get_latest_rates
    ):
        service = ExchangeRateService(MockedConversionRateCacheService())
        conversion_request = ConversionRequest(
            from_currency="USD", to_currency="USD", amount=Decimal(100.0)
        )
        conversion = service.get_conversion_from(request=conversion_request)
        assert conversion.rate == 1

    @patch.object(
        ExchangeRateService, "get_latest_rates", return_value=MOCK_ERROR_EXCHANGE_RATES
    )
    def test_error_response_expect_exception(self, mocked_get_latest_rates):
        service = ExchangeRateService(MockedConversionRateCacheService())
        conversion_request = ConversionRequest(
            from_currency="EUR", to_currency="USD", amount=Decimal(100.0)
        )
        with pytest.raises(ConversionRateServiceException):
            service.get_conversion_from(request=conversion_request)

    @patch.object(
        ExchangeRateService, "get_latest_rates", return_value=MOCK_EXCHANGE_RATES
    )
    def test_from_currency_is_equals_to_base_expect_correct_response(
        self,
        mocked_get_latest_rates,
    ):
        service = ExchangeRateService(MockedConversionRateCacheService())
        amount = Decimal(98.12)
        conversion_request = ConversionRequest(
            from_currency="EUR", to_currency="USD", amount=amount
        )
        conversion = service.get_conversion_from(request=conversion_request)
        assert (
            conversion.rate
            == MOCK_EXCHANGE_RATES["rates"][conversion_request.to_currency]
        )
        assert conversion.converted_amount == amount * Decimal(
            MOCK_EXCHANGE_RATES["rates"][conversion_request.to_currency]
        )

    @patch.object(
        ExchangeRateService, "get_latest_rates", return_value=MOCK_EXCHANGE_RATES
    )
    def test_to_currency_is_equals_to_base_expect_correct_response(
        self, mocked_get_latest_rates
    ):
        service = ExchangeRateService(MockedConversionRateCacheService())
        amount = Decimal(14.12)
        conversion_request = ConversionRequest(
            from_currency="USD", to_currency="EUR", amount=amount
        )
        conversion = service.get_conversion_from(request=conversion_request)
        assert conversion.rate == Decimal(1) / Decimal(
            MOCK_EXCHANGE_RATES["rates"][conversion_request.from_currency]
        )
        assert conversion.converted_amount == amount / Decimal(
            MOCK_EXCHANGE_RATES["rates"][conversion_request.from_currency]
        )

    @patch.object(
        ExchangeRateService, "get_latest_rates", return_value=MOCK_EXCHANGE_RATES
    )
    def test_both_currencies_are_different_from_base_expect_correct_response(
        self,
        mocked_get_latest_rates,
    ):
        service = ExchangeRateService(MockedConversionRateCacheService())
        amount = Decimal(0.50)
        conversion_request = ConversionRequest(
            from_currency="USD", to_currency="VEF", amount=amount
        )
        conversion = service.get_conversion_from(request=conversion_request)

        to_currency_rate = Decimal(
            MOCK_EXCHANGE_RATES["rates"][conversion_request.to_currency]
        )
        from_currency_rate = Decimal(
            MOCK_EXCHANGE_RATES["rates"][conversion_request.from_currency]
        )
        final_rate = to_currency_rate / from_currency_rate
        assert conversion.rate == final_rate
        assert conversion.converted_amount == amount * final_rate

    def test_get_datetime_from_timestamp(self):
        timestamp = MOCK_EXCHANGE_RATES["timestamp"]
        expected_datetime = "2024-05-30 18:29:04+00:00"
        assert expected_datetime == str(
            ExchangeRateService(
                MockedConversionRateCacheService()
            ).parse_timestamp_to_datetime(timestamp)
        )

    @freeze_time("2024-05-30")
    def test_todays_key_expect_full_year_month_day(self):
        assert (
            "2024-05-30"
            == ExchangeRateService(MockedConversionRateCacheService()).todays_key
        )

    @patch.object(requests, "get")
    @patch.object(MockedConversionRateCacheService, "save_rates")
    @patch.object(
        MockedConversionRateCacheService, "get_rates", return_value=MOCK_EXCHANGE_RATES
    )
    def test_get_latest_rates_expect_use_cache(
        self, mocked_cache_get, mocked_cache_set, mocked_get
    ):
        ExchangeRateService(MockedConversionRateCacheService()).get_latest_rates()
        assert mocked_cache_set.call_count == 0
        assert mocked_get.call_count == 0

    @patch.object(requests, "get")
    @patch.object(MockedConversionRateCacheService, "save_rates")
    @patch.object(MockedConversionRateCacheService, "get_rates", return_value=None)
    def test_get_latest_rates_expect_fetch_rates(
        self, mocked_cache_get, mocked_cache_set, mocked_get
    ):
        ExchangeRateService(MockedConversionRateCacheService()).get_latest_rates()
        assert mocked_cache_set.call_count == 1
        assert mocked_get.call_count == 1


@pytest.mark.django_db()
class TestConversionDbService:
    def test_user_has_no_conversions_expect_empty_list(self, user):
        service = ConversionDbService()
        assert service.listByUser(user_id=user.external_id) == []

    def test_user_has_conversions_expect_filled_list(
        self, user, teardown_conversions, django_user_model
    ):
        other_user = django_user_model.objects.create_user(
            email="other@email.com", password="something"
        )
        num_of_conversions_for_user = 2
        for _ in range(num_of_conversions_for_user):
            ConversionModel.objects.create(
                user=user,
                from_currency="USD",
                from_amount=Decimal(100.0),
                to_currency="USD",
                to_amount=Decimal(98.12),
                rate=Decimal(1.0),
                created_at=datetime.datetime.now(tz=datetime.timezone.utc),
            )

        ConversionModel.objects.create(
            user=other_user,
            from_currency="USD",
            from_amount=Decimal(100.0),
            to_currency="EUR",
            to_amount=Decimal(98.12),
            rate=Decimal(1.0),
            created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        )

        service = ConversionDbService()
        conversions = service.listByUser(user_id=user.external_id)
        assert len(conversions) == num_of_conversions_for_user

        conversions = service.listByUser(user_id=other_user.external_id)
        assert len(conversions) == 1

    def test_conversion_is_properly_created_expect_all_fields_properly_set(
        self, user, teardown_conversions
    ):
        conversion = Conversion(
            user_id=user.external_id,
            request=ConversionRequest(
                from_currency="EUR",
                to_currency="USD",
                amount=Decimal(98.12),
            ),
            response=ConversionResponse(
                converted_amount=Decimal(98.12),
                rate=Decimal(1.0),
                created_at=datetime.datetime.now(tz=datetime.timezone.utc),
            ),
        )

        service = ConversionDbService()
        created_conversion = service.create(conversion)

        assert created_conversion.id is not None
        assert created_conversion.user_id == user.external_id
        assert (
            created_conversion.request.from_currency == conversion.request.from_currency
        )
        assert created_conversion.request.to_currency == conversion.request.to_currency
        assert created_conversion.request.amount == conversion.request.amount
        assert (
            created_conversion.response.converted_amount
            == conversion.response.converted_amount
        )
        assert created_conversion.response.rate == conversion.response.rate
        assert created_conversion.response.created_at == conversion.response.created_at


class TestMidnightCache:
    freeze_time("2024-05-30 23:00:00+00:00")

    def test_calculate_midnight_offset(self):
        MidnightCache().calculate_seconds_until_midnight() == 3600
