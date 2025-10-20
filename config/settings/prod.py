# config/settings/prod.py
from .dev import *  # noqa
import os


DEBUG = False

# 운영 도메인/아이피 (쉼표 구분)
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "example.com").split(",")

# 운영 DB(PostgreSQL): 환경변수 존재 시 적용
if os.getenv("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB"),
            "USER": os.getenv("POSTGRES_USER"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
            "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }

# 보안 권장값
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
