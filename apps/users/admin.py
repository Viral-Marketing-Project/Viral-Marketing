# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # 목록 화면
    ordering = ("-date_joined",)
    list_display = ("email", "name", "nickname", "phone", "is_active", "is_staff", "last_login", "date_joined")
    list_filter = ("is_active", "is_staff")  # ✅ 요구사항: is_staff / is_active 기준 필터

    # 검색: 이메일/닉네임/휴대폰
    search_fields = ("email", "nickname", "phone")  # ✅ 요구사항 충족
    # (원하면 name도 추가 가능: "name",)

    # 상세 화면: 읽기 전용 필드
    readonly_fields = ("is_superuser", "last_login", "date_joined")  # ✅ 어드민 여부는 읽기 전용

    fieldsets = (
        ("기본 정보", {"fields": ("email", "password")}),
        ("개인 정보", {"fields": ("name", "nickname", "phone")}),
        # is_superuser를 보여주되 편집은 못 하게(readonly_fields에 포함)
        ("권한", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("중요 시각", {"fields": ("last_login", "date_joined")}),
    )

    # 생성 화면: is_superuser 제외(콘솔에서 createsuperuser로만 생성하도록)
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            # 어드민 여부는 읽기 전용이므로 생성 폼에서 제외
            "fields": ("email", "password1", "password2", "is_staff", "is_active"),
        }),
    )

    # 이메일을 사용자명 필드로 쓰는 BaseUserAdmin 기본 동작을 그대로 사용
