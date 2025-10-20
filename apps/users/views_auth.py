# apps/users/views_auth.py
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

User = get_user_model()

def _set_token_cookies(response, refresh: RefreshToken):
    """access/refresh 토큰을 HttpOnly 쿠키에 세팅"""
    cfg = settings.JWT_AUTH
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    # 만료 시간(초)
    access_exp = int(refresh.access_token.lifetime.total_seconds())
    refresh_exp = int(refresh.lifetime.total_seconds())

    # 공통 쿠키 옵션
    common = dict(
        httponly=True,
        secure=cfg["COOKIE_SECURE"],
        samesite=cfg["COOKIE_SAMESITE"],
        domain=cfg["COOKIE_DOMAIN"],
    )

    response.set_cookie(
        cfg["ACCESS_COOKIE_NAME"],
        access_token,
        max_age=access_exp,
        path=cfg["ACCESS_COOKIE_PATH"],
        **common,
    )
    response.set_cookie(
        cfg["REFRESH_COOKIE_NAME"],
        refresh_token,
        max_age=refresh_exp,
        path=cfg["REFRESH_COOKIE_PATH"],
        **common,
    )

def _clear_token_cookies(response):
    cfg = settings.JWT_AUTH
    response.delete_cookie(cfg["ACCESS_COOKIE_NAME"], path=cfg["ACCESS_COOKIE_PATH"], domain=cfg["COOKIE_DOMAIN"])
    response.delete_cookie(cfg["REFRESH_COOKIE_NAME"], path=cfg["REFRESH_COOKIE_PATH"], domain=cfg["COOKIE_DOMAIN"])

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = authenticate(request, email=email, password=password)
        if not user:
            return Response({"detail": "이메일 또는 비밀번호가 올바르지 않습니다."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({"detail": "이메일 인증이 완료되지 않았습니다."}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        resp = Response(
            {
                "detail": "로그인 성공",
                "user": {"id": str(user.pk), "email": user.email, "nickname": user.nickname, "name": user.name},
                "access_expires_in": int(refresh.access_token.lifetime.total_seconds()),
                "refresh_expires_in": int(refresh.lifetime.total_seconds()),
            },
            status=200,
        )
        _set_token_cookies(resp, refresh)
        return resp

class RefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        cfg = settings.JWT_AUTH
        token_str = request.data.get("refresh") or request.COOKIES.get(cfg["REFRESH_COOKIE_NAME"])
        if not token_str:
            return Response({"detail": "리프레시 토큰이 없습니다."}, status=400)
        try:
            old_refresh = RefreshToken(token_str)
            # rotate 설정이면 새로운 refresh가 생성됨
            new_refresh = RefreshToken.for_user(User.objects.get(id=old_refresh["user_id"]))
            # 블랙리스트 사용 시 이전 refresh 블랙리스트
            if settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION") and "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS:
                try:
                    BlacklistedToken.objects.get_or_create(token=OutstandingToken.objects.get(token=token_str))
                except OutstandingToken.DoesNotExist:
                    pass
        except (TokenError, InvalidToken) as e:
            return Response({"detail": f"유효하지 않은 토큰: {e}"}, status=401)

        resp = Response(
            {
                "detail": "토큰 갱신",
                "access_expires_in": int(new_refresh.access_token.lifetime.total_seconds()),
                "refresh_expires_in": int(new_refresh.lifetime.total_seconds()),
            },
            status=200,
        )
        _set_token_cookies(resp, new_refresh)
        return resp

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cfg = settings.JWT_AUTH

        # 1) 쿠키에서 refresh 가져오기
        raw_refresh = request.COOKIES.get(cfg["REFRESH_COOKIE_NAME"])

        # 2) 블랙리스트 활성화되어 있으면 현재 refresh를 블랙리스트에 추가
        if "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS and raw_refresh:
            try:
                refresh = RefreshToken(raw_refresh)
                jti = refresh["jti"]                                      # ✅ jti 추출
                ot = OutstandingToken.objects.get(jti=jti)                # ✅ OutstandingToken 찾기
                BlacklistedToken.objects.get_or_create(token=ot)          # ✅ 블랙리스트 등록
            except (OutstandingToken.DoesNotExist, TokenError, InvalidToken):
                # 토큰이 이미 만료/회수되었거나 형식이 잘못된 경우는 그냥 무시하고 진행
                pass

        # (선택) 보안을 더 강하게: 이 사용자의 다른 모든 refresh도 무효화하고 싶다면 아래 주석 해제
        # if "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS:
        #     for t in OutstandingToken.objects.filter(user=request.user):
        #         BlacklistedToken.objects.get_or_create(token=t)

        # 3) 쿠키 삭제
        resp = Response({"detail": "로그아웃 완료"}, status=status.HTTP_200_OK)
        _clear_token_cookies(resp)
        return resp