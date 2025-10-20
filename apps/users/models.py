import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        if not password:
            raise ValueError("Superuser must have a password")
        return self.create_user(email, password, **extra)

class User(AbstractBaseUser, PermissionsMixin):
    """
    users 테이블 (요구필드 반영)
    - 이메일(로그인), 비밀번호, 닉네임, 이름, 전화번호
    - 마지막 로그인, 스태프 여부, 관리자 여부, 계정 활성화 여부
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=254)   # 로그인 ID
    password = models.CharField(max_length=128)
    nickname = models.CharField(max_length=50, blank=True, null=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    is_staff = models.BooleanField(default=False)       # 스태프 여부
    is_superuser = models.BooleanField(default=False)   # 관리자 여부
    is_active = models.BooleanField(default=True)       # 계정 활성화 여부
    last_login = models.DateTimeField(blank=True, null=True)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email
