# config/settings/dev.py
# ---------------------------------------------
# (1) 환경변수 로딩 (상단부)
from pathlib import Path
import environ
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # .../django_mini_project
env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(env_file)

# 정적/미디어 (DEV)
STATIC_URL = "/static/"                       # ✅ 필수
STATICFILES_DIRS = [BASE_DIR / "static"]      # (선택)
MEDIA_URL = "/media/"                         # (선택)
MEDIA_ROOT = BASE_DIR / "media"               # (선택)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-change-me")

# (2) 기본 세팅
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# (3) 앱 등록
INSTALLED_APPS = [
    # Django 기본앱...
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # 서드파티
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",

    # 로컬 앱
    "apps.users",
    "apps.banking",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",     # ✅ admin에 필수
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # ✅ admin에 필수
    "django.contrib.messages.middleware.MessageMiddleware",     # ✅ admin에 필수
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",  # ✅ 필수
        "DIRS": [BASE_DIR / "templates"],  # 없으면 빈 리스트여도 OK
        "APP_DIRS": True,                  # 앱 내 templates/ 사용
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",   # admin에 자주 필요
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# URL / WSGI
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# 사용자 모델
AUTH_USER_MODEL = "users.User"

# (4) DRF / drf-spectacular
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # ✅ JWT를 기본 인증으로 (쿠키 우선 인증 클래스)
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.users.auth.CookieJWTAuthentication",
    ],
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Django Mini Project API",
    "VERSION": "1.0.0",
}

# (5) DB (env 값 사용)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="appdb"),
        "USER": env("POSTGRES_USER", default="appuser"),
        "PASSWORD": env("POSTGRES_PASSWORD", default=""),
        "HOST": env("POSTGRES_HOST", default="127.0.0.1"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

# (6) 이메일 (개발은 콘솔 출력)
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")
# (실서버 SMTP 쓸 땐 .env에 넣고 주석 해제)
# EMAIL_HOST = env("EMAIL_HOST", default=None)
# EMAIL_PORT = env.int("EMAIL_PORT", default=587)
# EMAIL_HOST_USER = env("EMAIL_HOST_USER", default=None)
# EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default=None)
# EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

# ---------------------------------------------
# ✅ SimpleJWT & 쿠키 기반 설정
# ---------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# 쿠키 관련 공통 상수 (뷰에서 사용)
JWT_AUTH = {
    "ACCESS_COOKIE_NAME": "access_token",
    "REFRESH_COOKIE_NAME": "refresh_token",
    "COOKIE_SECURE": False,       # dev=False, prod=True(HTTPS)
    "COOKIE_SAMESITE": "Lax",     # 크로스도메인 필요 시 prod에서 "None" + Secure=True
    "COOKIE_DOMAIN": None,        # 필요시 ".example.com" 등
    "ACCESS_COOKIE_PATH": "/",
    "REFRESH_COOKIE_PATH": "/api/auth/refresh/",
}
