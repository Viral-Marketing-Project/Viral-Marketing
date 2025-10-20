from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path("admin/", admin.site.urls),

    # OpenAPI 스키마 & 문서
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # 인증/회원가입
    path("api/auth/", include("apps.users.urls")),

    # 계좌/거래 (urls 파일이 비어 있어도 include 가능)
    path("api/accounts/", include("apps.banking.urls")),
]
