from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from rest_framework import serializers
from .tokens import email_verification_token

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("email", "password", "nickname", "name", "phone")

    def create(self, validated_data):
        raw = validated_data.pop("password")
        user = User(**validated_data)
        user.is_active = False                   # 이메일 인증 전까지 비활성
        user.set_password(raw)                  # ✅ 해시 저장
        user.save()
        return user

    def send_verification_email(self, user, request):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        verify_path = f"/api/auth/verify-email/?uid={uid}&token={token}"
        verify_url = request.build_absolute_uri(verify_path)
        send_mail(
            subject="[Django Mini Project] 이메일 인증을 완료해 주세요",
            message=f"아래 링크를 클릭해서 이메일 인증을 완료하세요:\n{verify_url}",
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )
