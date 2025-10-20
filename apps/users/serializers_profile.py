# apps/users/serializers_profile.py
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "nickname", "name", "phone", "date_joined", "last_login")
        read_only_fields = ("id", "email", "date_joined", "last_login")  # 이메일 수정 금지(권장)

    def update(self, instance, validated_data):
        # 필요한 경우 추가 검증/정합성 체크 가능
        return super().update(instance, validated_data)
