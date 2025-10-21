# apps/banking/serializers_transactions.py
from rest_framework import serializers
from .models import TransactionHistory, TRANSACTION_IO, TRANSACTION_METHOD

class TransactionCreateSerializer(serializers.Serializer):
    account_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    io_type = serializers.ChoiceField(choices=TRANSACTION_IO)        # "DEPOSIT" | "WITHDRAW"
    method = serializers.ChoiceField(choices=TRANSACTION_METHOD)     # "CASH"|"TRANSFER"|...
    description = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("금액은 0보다 커야 합니다.")
        return value


class TransactionSerializer(serializers.ModelSerializer):
    """조회/상세 응답용 — 요구 4) 필드 포함"""
    class Meta:
        model = TransactionHistory
        fields = ("id", "account", "amount", "balance_after", "description",
                  "io_type", "method", "created_at")
        read_only_fields = fields


class TransactionUpdateSerializer(serializers.ModelSerializer):
    """
    수정 허용 필드만 노출 (안전)
    - 금액/입출금타입을 바꾸면 잔액 재계산 등 장부 재작성 이슈가 생깁니다.
      여기서는 설명/거래방법만 수정하도록 제한합니다.
      (정말 필요하면 관리자 전용 별도 엔드포인트로 구현 권장)
    """
    class Meta:
        model = TransactionHistory
        fields = ("description", "method")
