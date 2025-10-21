# apps/banking/serializers_accounts.py
from rest_framework import serializers
from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    """
    조회/상세 응답용 시리얼라이저.
    - 계좌의 식별/기본 정보는 모두 read-only
    - 어떤 경로로든 update()가 호출되면 막는다(이중 안전장치)
    """
    class Meta:
        model = Account
        fields = (
            "id",
            "user",           # 기본은 user의 pk가 보임. 원하면 SerializerMethodField로 가려도 OK
            "bank_code",
            "account_number",
            "account_type",
            "balance",
            "created_at",
            "updated_at",
        )
        # 생성 이후 수정 불가 필드 + 시스템 필드
        read_only_fields = (
            "id",
            "user",
            "bank_code",
            "account_number",
            "account_type",
            "balance",
            "created_at",
            "updated_at",
        )

    def update(self, instance, validated_data):  # 이중 안전장치
        raise serializers.ValidationError("계좌 정보는 생성 이후 수정할 수 없습니다.")


class AccountCreateSerializer(serializers.ModelSerializer):
    """
    신규 생성용 시리얼라이저.
    - user는 서버에서 request.user로 강제 바인딩
    - (bank_code, account_number) 전역 중복 사전 검증
    """
    class Meta:
        model = Account
        fields = ("bank_code", "account_number", "account_type")

    def validate(self, attrs):
        # 계좌번호 형식(간단): 숫자만
        num = attrs.get("account_number", "")
        if not str(num).isdigit():
            raise serializers.ValidationError({"account_number": "계좌번호는 숫자만 입력해 주세요."})

        # 전역 고유 제약 사전 검증 (모델의 UniqueConstraint 최종 방어와 중복)
        bc = attrs.get("bank_code")
        if Account.objects.filter(bank_code=bc, account_number=num).exists():
            raise serializers.ValidationError("이미 등록된 계좌(은행코드+계좌번호)입니다.")
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        # body로 user가 와도 무시하고 현재 로그인 유저로 강제
        return Account.objects.create(user=user, **validated_data)
