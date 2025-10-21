# config/urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # ---- API 라우팅 ----
    path("api/auth/", include("apps.users.urls", namespace="users")),     # 유저/인증
    path("api/", include("apps.banking.urls", namespace="banking")),      # 계좌/거래

    # ---- API 스키마 & 문서 ----
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
