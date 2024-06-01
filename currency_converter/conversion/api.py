from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, exceptions, status
from django.contrib.auth import get_user_model

from conversion.domain import Conversion, ConversionRequest
from conversion.services import (
    ConversionDbService,
    ConversionService,
    ExchangeRateService,
)


class InputSerializer(serializers.Serializer):
    from_currency = serializers.CharField()
    to_currency = serializers.CharField()
    amount = serializers.DecimalField(max_digits=5, decimal_places=2)
    user_id = serializers.CharField()


class OutputSerializer(InputSerializer):
    id = serializers.IntegerField()
    to_amount = serializers.DecimalField(max_digits=5, decimal_places=2)
    rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    created_at = serializers.DateTimeField()


class CreateConversionView(APIView):
    def post(self, request):
        serializer = InputSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            User = get_user_model()
            try:
                User.objects.get(external_id=serializer.validated_data["user_id"])
            except User.DoesNotExist:
                raise exceptions.PermissionDenied()

            conversion_request = ConversionRequest(
                from_currency=serializer.validated_data["from_currency"],
                to_currency=serializer.validated_data["to_currency"],
                amount=serializer.validated_data["amount"],
            )

            conversion_service = ConversionService(ExchangeRateService())
            conversion_response = conversion_service.convert_currency(
                conversion_request
            )

            conversion = Conversion(
                user_id=serializer.validated_data["user_id"],
                request=conversion_request,
                response=conversion_response,
            )
            successful_conversion = ConversionDbService().create(conversion)
            return Response(
                OutputSerializer(
                    {
                        "id": successful_conversion.id,
                        "user_id": successful_conversion.user_id,
                        "from_currency": successful_conversion.request.from_currency,
                        "amount": successful_conversion.request.amount,
                        "to_currency": successful_conversion.request.to_currency,
                        "to_amount": successful_conversion.response.converted_amount,
                        "rate": successful_conversion.response.rate,
                        "created_at": successful_conversion.response.created_at,
                    }
                ).data,
                status=status.HTTP_200_OK,
            )


class GetUserConversionsView(APIView):
    def get(self, request): ...
