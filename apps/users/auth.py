# apps/users/auth.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings

class CookieJWTAuthentication(JWTAuthentication):
    """
    1) Authorization 헤더 Bearer 우선
    2) 없으면 access_token 쿠키에서 읽음
    """
    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        # 헤더 없으면 쿠키 확인
        access_cookie_name = settings.JWT_AUTH["ACCESS_COOKIE_NAME"]
        raw_token = request.COOKIES.get(access_cookie_name)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
