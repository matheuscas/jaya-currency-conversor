from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, exceptions, status
from django.contrib.auth import get_user_model

from conversion.domain import Conversion, ConversionRequest
from conversion.services import (
    ConversionDbService,
    ConversionRatesCacheService,
    ConversionService,
    ExchangeRatesAPI,
    MidnightCache,
)
from conversion.exceptions import (
    ConversionRateServiceException,
    CurrencyNotFoundException,
)
from drf_spectacular.utils import extend_schema, OpenApiExample

import structlog

logger = structlog.get_logger(__name__)


class ConversionRequestSerializer(serializers.Serializer):
    from_currency = serializers.CharField()
    to_currency = serializers.CharField()
    amount = serializers.DecimalField(max_digits=5, decimal_places=2)
    user_id = serializers.CharField()


class ConversionResponseSerializer(ConversionRequestSerializer):
    id = serializers.IntegerField()
    to_amount = serializers.DecimalField(max_digits=5, decimal_places=2)
    rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    rates_timestamp = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S %Z%z")


class CreateConversionView(APIView):
    @extend_schema(
        request=ConversionRequestSerializer,
        responses={
            200: ConversionResponseSerializer,
        },
        description="Request a new conversion",
        tags=["Conversions"],
        examples=[
            OpenApiExample(
                "New conversion request example",
                value={
                    "from_currency": "USD",
                    "to_currency": "EUR",
                    "amount": 100,
                    "user_id": "user_123",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Conversion response example",
                value={
                    "id": 1,
                    "user_id": "user_123",
                    "from_currency": "USD",
                    "amount": 100,
                    "to_currency": "EUR",
                    "to_amount": 108.40,
                    "rate": 1.16,
                    "rates_timestamp": "2024-06-02 15:56:58 UTC+0000",
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = ConversionRequestSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            User = get_user_model()
            try:
                User.objects.get(external_id=serializer.validated_data["user_id"])
            except User.DoesNotExist:
                logger.exception("User does not exist", **serializer.validated_data)
                raise exceptions.PermissionDenied()

            conversion_request = ConversionRequest(
                from_currency=serializer.validated_data["from_currency"],
                to_currency=serializer.validated_data["to_currency"],
                amount=serializer.validated_data["amount"],
            )

            try:
                conversion_service = ConversionService(
                    ExchangeRatesAPI(ConversionRatesCacheService(MidnightCache()))
                )
                conversion_response = conversion_service.convert_currency(
                    conversion_request
                )
            except CurrencyNotFoundException as cnfe:
                logger.exception(str(cnfe), **serializer.validated_data)
                raise exceptions.ValidationError(str(cnfe))
            except ConversionRateServiceException as crse:
                logger.exception(str(crse), **serializer.validated_data)
                raise exceptions.APIException(detail=str(crse))
            except Exception as e:
                # any other exception like from requests.get
                logger.exception(str(e), **serializer.validated_data)
                api_exception = exceptions.APIException(detail=str(e))
                api_exception.status_code = e.response.status_code
                raise api_exception

            conversion = Conversion(
                user_id=serializer.validated_data["user_id"],
                request=conversion_request,
                response=conversion_response,
            )
            successful_conversion = ConversionDbService().create(conversion)
            formatted_conversion = {
                "id": successful_conversion.id,
                "user_id": successful_conversion.user_id,
                "from_currency": successful_conversion.request.from_currency,
                "amount": successful_conversion.request.amount,
                "to_currency": successful_conversion.request.to_currency,
                "to_amount": successful_conversion.response.converted_amount,
                "rate": successful_conversion.response.rate,
                "rates_timestamp": successful_conversion.response.rates_timestamp,
            }
            logger.info("Conversion created", **formatted_conversion)
            return Response(
                ConversionResponseSerializer(formatted_conversion).data,
                status=status.HTTP_201_CREATED,
            )


class GetUserConversionsView(APIView):
    @extend_schema(
        responses={200: ConversionResponseSerializer},
        description="Request user's conversions",
        tags=["Conversions"],
        examples=[
            OpenApiExample(
                "User's conversions response example",
                value=[
                    {
                        "id": 1,
                        "user_id": "user_123",
                        "from_currency": "USD",
                        "amount": 100,
                        "to_currency": "EUR",
                        "to_amount": 108.40,
                        "rate": 1.16,
                        "rates_timestamp": "2024-06-02 15:56:58 UTC+0000",
                    },
                    {
                        "id": 2,
                        "user_id": "user_123",
                        "from_currency": "USD",
                        "amount": 100,
                        "to_currency": "BRL",
                        "to_amount": 523.00,
                        "rate": 5.23,
                        "rates_timestamp": "2024-06-02 16:56:58 UTC+0000",
                    },
                ],
                response_only=True,
            ),
        ],
    )
    def get(self, request, user_id):
        User = get_user_model()
        try:
            User.objects.get(external_id=user_id)
        except User.DoesNotExist:
            logger.exception("User does not exist", user_id=user_id)
            raise exceptions.PermissionDenied()

        user_conversions = ConversionDbService().listByUser(user_id=user_id)
        output_conversions = []
        for conversion in user_conversions:
            output_conversions.append(
                {
                    "id": conversion.id,
                    "user_id": conversion.user_id,
                    "from_currency": conversion.request.from_currency,
                    "amount": conversion.request.amount,
                    "to_currency": conversion.request.to_currency,
                    "to_amount": conversion.response.converted_amount,
                    "rate": conversion.response.rate,
                    "rates_timestamp": conversion.response.rates_timestamp,
                }
            )
        return Response(
            ConversionResponseSerializer(output_conversions, many=True).data,
            status=status.HTTP_200_OK,
        )
