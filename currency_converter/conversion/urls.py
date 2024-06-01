from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from django.urls import path

from conversion.api import CreateConversionView, GetUserConversionsView

urlpatterns = [
    path(
        "api/users/<str:user_id>/conversions/",
        GetUserConversionsView.as_view(),
        name="conversions-user-list",
    ),
    path("api/conversions/", CreateConversionView.as_view(), name="conversion-create"),
    # YOUR PATTERNS
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI:
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
