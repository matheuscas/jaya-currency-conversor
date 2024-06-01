from unittest.mock import patch
import pytest
import datetime
from django.urls import reverse
from pytz import timezone  # type: ignore
from rest_framework import status

from conversion.services import ExchangeRateService
from conversion.test_services import MOCK_ERROR_EXCHANGE_RATES, MOCK_EXCHANGE_RATES
from conversion.models import Conversion as ConversionModel  # type: ignore


DATE_FORMAT = "%Y-%m-%d %H:%M:%S %Z%z"


class TestCreateConversionView:
    @pytest.mark.parametrize(
        "missing_field", ["from_currency", "to_currency", "amount", "user_id"]
    )
    def test_field_is_missing_expect_exception(self, client, missing_field):
        payload = {
            "from_currency": "EUR",
            "to_currency": "USD",
            "amount": 98.12,
            "user_id": "123",
        }
        payload.pop(missing_field)
        response = client.post(reverse("conversion-create"), payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_user_does_not_exist_expect_exception_status_400(self, client, user):
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
        ExchangeRateService, "get_latest_rates", return_value=MOCK_EXCHANGE_RATES
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
    ):
        payload = {
            "from_currency": from_curreny,
            "to_currency": to_currency,
            "amount": amount,
            "user_id": user.external_id,
        }
        response = client.post(reverse("conversion-create"), payload, format="json")
        data = response.json()
        assert response.status_code == status.HTTP_200_OK
        assert data["to_amount"] == converted_amount
        assert data["id"] is not None
        assert data["user_id"] == user.external_id

    @pytest.mark.parametrize(
        "from_currency, to_currency",
        [
            ("EUR", "YYY"),
            ("XXX", "USD"),
        ],
    )
    @patch.object(
        ExchangeRateService, "get_latest_rates", return_value=MOCK_EXCHANGE_RATES
    )
    def test_invalid_currency_expect_exception_status_400(
        self, mocked_get_latest_rates, from_currency, to_currency, client, user
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
        ExchangeRateService, "get_latest_rates", return_value=MOCK_ERROR_EXCHANGE_RATES
    )
    def test_failed_response_expect_exception_status_relative_to_external_api(
        self, mocked_get_latest_rates, client, user
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


@pytest.mark.django_db()
class TestGetUserConversionsView:
    def test_user_has_no_conversions_expect_empty_list(self, client, user):
        response = client.get(reverse("conversions-user-list", args=[user.external_id]))
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_user_has_conversions_expect_filled_list(
        self, client, user, teardown_conversions
    ):
        conversion_item = ConversionModel.objects.create(
            user=user,
            from_currency="EUR",
            from_amount=100,
            to_currency="USD",
            to_amount=108.40,
            rate=1.2,
            created_at=datetime.datetime.now(timezone("UTC")),
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
        assert data[0]["created_at"] == conversion_item.created_at.strftime(DATE_FORMAT)

    def test_user_does_not_exist_expect_exception_status_400(self, client, user):
        response = client.get(reverse("conversions-user-list", args=[1]))
        assert response.status_code == status.HTTP_403_FORBIDDEN
