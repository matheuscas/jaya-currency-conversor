from django.urls import path

from conversion.api import CreateConversionView, GetUserConversionsView

urlpatterns = [
    path(
        "api/users/<str:user_id>/conversions/",
        GetUserConversionsView.as_view(),
        name="conversions-user-list",
    ),
    path("api/conversions/", CreateConversionView.as_view(), name="conversion-create"),
]
