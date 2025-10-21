# apps/users/serializers_auth.py
from rest_framework import serializers

class LoginInputSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

class LoginResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    user = serializers.DictField()
    access_expires_in = serializers.IntegerField()
    refresh_expires_in = serializers.IntegerField()
