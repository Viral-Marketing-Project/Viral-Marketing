from django.urls import path
from .views import RegisterView, VerifyEmailView
from .views_auth import LoginView, RefreshView, LogoutView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),

    # ✅ JWT 쿠키 인증
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
]


