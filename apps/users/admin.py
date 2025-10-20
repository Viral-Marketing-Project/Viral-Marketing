# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("email", "name", "nickname", "is_active", "is_staff", "last_login", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "name", "nickname", "phone")

    fieldsets = (
        ("기본 정보", {"fields": ("email", "password")}),
        ("개인 정보", {"fields": ("name", "nickname", "phone")}),
        ("권한", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("중요 시각", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_superuser", "is_active"),
        }),
    )

    # username 대신 email 로그인이라서 username_field 재정의 필요 없음 (BaseUserAdmin가 USERNAME_FIELD 읽음)
