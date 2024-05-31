from unittest.mock import patch
import pytest
from django.urls import reverse
from rest_framework import status

from conversion.services import ExchangeRateService
from conversion.test_services import MOCK_EXCHANGE_RATES


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

    # TODO test exceptions comming from ExchangeRateService


class TestGetUserConversionsView:
    def test_user_has_no_conversions_expect_empty_list(self):
        pass

    def test_user_has_conversions_expect_filled_list(self):
        pass

    def test_user_does_not_exist_expect_exception_status_400(self):
        pass
