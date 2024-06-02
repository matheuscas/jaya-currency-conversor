from decimal import Decimal
from unittest.mock import patch
import pytest
import datetime
from django.urls import reverse
from pytz import timezone  # type: ignore
from rest_framework import status

from conversion.services import ExchangeRatesAPI
from conversion.test_services import MOCK_ERROR_EXCHANGE_RATES, MOCK_EXCHANGE_RATES
from conversion.models import Conversion as ConversionModel  # type: ignore
from conversion.api import CreateConversionView, GetUserConversionsView  # type: ignore


DATE_FORMAT = "%Y-%m-%d %H:%M:%S %Z%z"


class TestCreateConversionView:
    @pytest.fixture
    def disable_throttling(self):
        throttling_clases = CreateConversionView.throttle_classes
        CreateConversionView.throttle_classes = ()
        yield
        CreateConversionView.throttle_classes = throttling_clases

    @pytest.mark.parametrize(
        "missing_field", ["from_currency", "to_currency", "amount", "user_id"]
    )
    def test_field_is_missing_expect_exception(
        self, client, missing_field, disable_throttling
    ):
        payload = {
            "from_currency": "EUR",
            "to_currency": "USD",
            "amount": 98.12,
            "user_id": "123",
        }
        payload.pop(missing_field)
        response = client.post(reverse("conversion-create"), payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_user_does_not_exist_expect_exception_status_400(
        self, client, user, disable_throttling
    ):
        payload = {
            "from_currency": "EUR",
            "to_currency": "USD",
            "amount": 98.12,
            "user_id": "123",
        }
        response = client.post(reverse("conversion-create"), payload, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "from_curreny, to_currency, amount, converted_amount",
        [
            ("EUR", "USD", 100, "108.40"),
            ("USD", "EUR", 200, "184.51"),
            ("FJD", "BRL", 2.5, "5.76"),
            ("BRL", "GBP", 500, "75.44"),
        ],
    )
    @patch.object(
        ExchangeRatesAPI, "get_latest_rates", return_value=MOCK_EXCHANGE_RATES
    )
    def test_success_conversion_expect_correct_response_format(
        self,
        mocked_get_latest_rates,
        from_curreny,
        to_currency,
        amount,
        converted_amount,
        client,
        user,
        disable_throttling,
    ):
        payload = {
            "from_currency": from_curreny,
            "to_currency": to_currency,
            "amount": amount,
            "user_id": user.external_id,
        }
        response = client.post(reverse("conversion-create"), payload, format="json")
        data = response.json()
        assert response.status_code == status.HTTP_201_CREATED
        assert data["to_amount"] == converted_amount
        assert data["id"] is not None
        assert data["user_id"] == user.external_id

        assert data["from_currency"] == from_curreny
        assert Decimal(data["amount"]) == Decimal(amount)
        assert data["to_currency"] == to_currency
        assert data["rate"]
        assert data["rates_timestamp"]
        assert data["created_at"]

    @pytest.mark.parametrize(
        "from_currency, to_currency",
        [
            ("EUR", "YYY"),
            ("XXX", "USD"),
        ],
    )
    @patch.object(
        ExchangeRatesAPI, "get_latest_rates", return_value=MOCK_EXCHANGE_RATES
    )
    def test_invalid_currency_expect_exception_status_400(
        self,
        mocked_get_latest_rates,
        from_currency,
        to_currency,
        client,
        user,
        disable_throttling,
    ):
        payload = {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": 98.12,
            "user_id": user.external_id,
        }
        response = client.post(reverse("conversion-create"), payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch.object(
        ExchangeRatesAPI, "get_latest_rates", return_value=MOCK_ERROR_EXCHANGE_RATES
    )
    def test_failed_response_expect_exception_status_relative_to_external_api(
        self, mocked_get_latest_rates, client, user, disable_throttling
    ):
        payload = {
            "from_currency": "EUR",
            "to_currency": "USD",
            "amount": 98.12,
            "user_id": user.external_id,
        }
        response = client.post(reverse("conversion-create"), payload, format="json")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert (
            response.json()["detail"]
            == f"{MOCK_ERROR_EXCHANGE_RATES['error']['code']}: {MOCK_ERROR_EXCHANGE_RATES['error']['info']}"
        )

    @patch.object(
        ExchangeRatesAPI, "get_latest_rates", return_value=MOCK_EXCHANGE_RATES
    )
    def test_throttling_expect_error_429(self, mocked_get_latest_rates, client, user):
        for request_num in range(101):
            response = client.post(
                reverse("conversion-create"),
                {
                    "from_currency": "EUR",
                    "to_currency": "USD",
                    "amount": 100,
                    "user_id": user.external_id,
                },
                format="json",
            )
            if request_num == 100:
                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            else:
                print(f"{request_num=}")
                assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db()
class TestGetUserConversionsView:
    @pytest.fixture
    def disable_throttling(self):
        throttling_clases = GetUserConversionsView.throttle_classes
        GetUserConversionsView.throttle_classes = ()
        yield
        GetUserConversionsView.throttle_classes = throttling_clases

    def test_user_has_no_conversions_expect_empty_list(
        self, client, user, disable_throttling
    ):
        response = client.get(reverse("conversions-user-list", args=[user.external_id]))
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_user_has_conversions_expect_filled_list(
        self, client, user, teardown_conversions, disable_throttling
    ):
        conversion_item = ConversionModel.objects.create(
            user=user,
            from_currency="EUR",
            from_amount=100,
            to_currency="USD",
            to_amount=108.40,
            rate=1.2,
            rates_timestamp=datetime.datetime.now(timezone("UTC")),
        )

        response = client.get(reverse("conversions-user-list", args=[user.external_id]))
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["user_id"] == user.external_id
        assert data[0]["from_currency"] == "EUR"
        assert data[0]["amount"] == "100.00"
        assert data[0]["to_currency"] == "USD"
        assert data[0]["to_amount"] == "108.40"
        assert data[0]["rate"] == "1.20"
        assert data[0]["rates_timestamp"] == conversion_item.rates_timestamp.strftime(
            DATE_FORMAT
        )
        assert data[0]["created_at"] == conversion_item.created_at.strftime(DATE_FORMAT)

    def test_user_does_not_exist_expect_exception_status_400(
        self, client, user, disable_throttling
    ):
        response = client.get(reverse("conversions-user-list", args=[1]))
        assert response.status_code == status.HTTP_403_FORBIDDEN
