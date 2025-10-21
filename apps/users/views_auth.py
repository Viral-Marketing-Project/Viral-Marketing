# apps/users/views_auth.py
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

# drf-spectacular (Swagger 문서에 입력 폼/응답 스키마가 보이도록)
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
    inline_serializer,
)
from rest_framework import serializers

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


# ---------- 로그인 ----------
@extend_schema(
    summary="로그인 (쿠키에 JWT 저장)",
    description="이메일/비밀번호로 로그인하고 access/refresh 토큰을 HttpOnly 쿠키에 저장합니다.",
    request=inline_serializer(
        name="LoginInput",
        fields={
            "email": serializers.EmailField(),
            "password": serializers.CharField(write_only=True),
        },
    ),
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name="LoginResponse",
                fields={
                    "detail": serializers.CharField(),
                    "user": inline_serializer(
                        name="LoginUser",
                        fields={
                            "id": serializers.CharField(),
                            "email": serializers.EmailField(),
                            "nickname": serializers.CharField(allow_null=True, required=False),
                            "name": serializers.CharField(allow_null=True, required=False),
                        },
                    ),
                    "access_expires_in": serializers.IntegerField(),
                    "refresh_expires_in": serializers.IntegerField(),
                },
            )
        )
    },
    examples=[
        OpenApiExample(
            "Example",
            value={"email": "me@example.com", "password": "pass1234"},
            request_only=True,
        )
    ],
)
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
                "user": {
                    "id": str(user.pk),
                    "email": user.email,
                    "nickname": getattr(user, "nickname", None),
                    "name": getattr(user, "name", None),
                },
                "access_expires_in": int(refresh.access_token.lifetime.total_seconds()),
                "refresh_expires_in": int(refresh.lifetime.total_seconds()),
            },
            status=200,
        )
        _set_token_cookies(resp, refresh)
        return resp


# ---------- 토큰 리프레시 ----------
@extend_schema(
    summary="토큰 리프레시",
    description=(
        "쿠키의 refresh 토큰(권장) 또는 요청 바디의 `refresh` 값을 사용해 "
        "새 access(+선택적으로 새 refresh)를 발급합니다. "
        "ROTATE_REFRESH_TOKENS=True인 경우 이전 refresh는 블랙리스트에 등록됩니다."
    ),
    request=inline_serializer(
        name="RefreshInput",
        fields={"refresh": serializers.CharField(required=False)},
    ),
    responses={
        200: OpenApiResponse(
            response=inline_serializer(
                name="RefreshResponse",
                fields={
                    "detail": serializers.CharField(),
                    "access_expires_in": serializers.IntegerField(),
                    "refresh_expires_in": serializers.IntegerField(),
                },
            )
        )
    },
    examples=[
        OpenApiExample(
            "Body에 refresh를 직접 전달하는 경우(옵션)",
            value={"refresh": "eyJhbGciOiJIUzI1..."},
            request_only=True,
        )
    ],
)
class RefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        cfg = settings.JWT_AUTH
        token_str = request.data.get("refresh") or request.COOKIES.get(cfg["REFRESH_COOKIE_NAME"])
        if not token_str:
            return Response({"detail": "리프레시 토큰이 없습니다."}, status=400)

        try:
            # 기존 refresh 파싱
            old_refresh = RefreshToken(token_str)
            user_id = old_refresh["user_id"]
            user = User.objects.get(id=user_id)

            # 새 refresh 발급(회전 시나리오)
            new_refresh = RefreshToken.for_user(user)

            # 회전 설정 + 블랙리스트 앱이 있으면 이전 refresh를 블랙리스트 등록
            if (
                settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION")
                and "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS
            ):
                try:
                    jti = old_refresh["jti"]
                    ot = OutstandingToken.objects.get(jti=jti)
                    BlacklistedToken.objects.get_or_create(token=ot)
                except OutstandingToken.DoesNotExist:
                    # 이미 만료/회수됐을 수 있음 → 무시
                    pass

        except (TokenError, InvalidToken) as e:
            return Response({"detail": f"유효하지 않은 토큰: {e}"}, status=401)
        except User.DoesNotExist:
            return Response({"detail": "유효하지 않은 사용자입니다."}, status=401)

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


# ---------- 로그아웃 ----------
@extend_schema(
    summary="로그아웃",
    description="현재 refresh 토큰을 블랙리스트에 등록하고, access/refresh 쿠키를 제거합니다.",
    responses={200: OpenApiResponse(description='{"detail": "로그아웃 완료"}')},
)
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
                jti = refresh["jti"]
                ot = OutstandingToken.objects.get(jti=jti)
                BlacklistedToken.objects.get_or_create(token=ot)
            except (OutstandingToken.DoesNotExist, TokenError, InvalidToken):
                # 이미 만료/회수/형식 오류 → 무시하고 진행
                pass

        # (선택) 이 사용자의 다른 모든 refresh도 무효화하려면 주석 해제
        # if "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS:
        #     for t in OutstandingToken.objects.filter(user=request.user):
        #         BlacklistedToken.objects.get_or_create(token=t)

        # 3) 쿠키 삭제
        resp = Response({"detail": "로그아웃 완료"}, status=status.HTTP_200_OK)
        _clear_token_cookies(resp)
        return resp
