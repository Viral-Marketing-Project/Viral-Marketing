# apps/banking/models.py
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


# ---- CHOICES ----
BANK_CODES = [
    ("KAKAO", "카카오뱅크"),
    ("KB", "KB국민"),
    ("NH", "농협"),
    ("IBK", "기업"),
    ("SC", "SC제일"),
    ("HANA", "하나"),
    ("WOORI", "우리"),
    ("SHINHAN", "신한"),
    ("ETC", "기타"),
]

ACCOUNT_TYPES = [
    ("DEMAND", "입출금통장"),     # 단순 입출금
    ("OVERDRAFT", "마이너스 통장"),
    ("SAVINGS", "예·적금"),
    ("ETC", "기타"),
]

TRANSACTION_IO = [
    ("DEPOSIT", "입금"),
    ("WITHDRAW", "출금"),
]

TRANSACTION_METHOD = [
    ("CASH", "현금"),
    ("TRANSFER", "계좌 이체"),
    ("AUTO", "자동 이체"),
    ("CARD", "카드 결제"),
    ("ETC", "기타"),
]


class Account(models.Model):
    """
    accounts 테이블
    - 유저(FK), 계좌번호, 은행코드, 계좌종류, 잔액, 생성/수정시각
    - (user, bank_code, account_number) 조합 유니크 → 한 유저가 같은 계좌를 중복 등록 불가
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accounts")
    account_number = models.CharField(max_length=32)  # 하이픈 제거 저장 권장
    bank_code = models.CharField(max_length=16, choices=BANK_CODES)
    account_type = models.CharField(max_length=16, choices=ACCOUNT_TYPES, default="DEMAND")
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "bank_code", "account_number"],
                name="uq_user_bank_acct",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_acct_user_created"),
        ]
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.bank_code}-{self.account_number}"

    # --- 불변 필드 보호: 생성 이후 bank_code/account_number/account_type 변경 불가 ---
    def clean(self):
        if self._state.adding or not self.pk:
            return

        # 기존 레코드와 비교하여 불변 필드가 변경되면 막기
        old = Account.objects.get(pk=self.pk)
        immutable_changed = (
            old.bank_code != self.bank_code
            or old.account_number != self.account_number
            or old.account_type != self.account_type
        )
        if immutable_changed:
            raise ValidationError("계좌의 은행/계좌번호/계좌종류는 생성 이후 수정할 수 없습니다.")

    def save(self, *args, **kwargs):
        # 필드/비즈니스 검증 수행 (clean() 포함)
        self.full_clean()
        return super().save(*args, **kwargs)

    @transaction.atomic
    def apply_transaction(
        self,
        *,
        amount: Decimal,
        io_type: str,
        method: str,
        description: str = "",
        when=None,
    ):
        """
        동시성 안전 입출금 처리:
        - 자기 계좌 행을 select_for_update로 잠금
        - 금액은 양수로 가정(입금/출금은 io_type으로 구분)
        - 잔액 갱신 + 거래 레코드 생성
        """
        if amount <= 0:
            raise ValidationError("거래 금액은 0보다 커야 합니다.")
        if io_type not in dict(TRANSACTION_IO):
            raise ValidationError("허용되지 않는 입출금 타입입니다.")
        if method not in dict(TRANSACTION_METHOD):
            raise ValidationError("허용되지 않는 거래 타입입니다.")

        # 🔒 동시성 잠금 후 최신 잔액 기준으로 처리
        acc = Account.objects.select_for_update().get(pk=self.pk)

        if io_type == "WITHDRAW" and acc.balance < amount:
            raise ValidationError("잔액 부족")

        new_balance = acc.balance + amount if io_type == "DEPOSIT" else acc.balance - amount
        acc.balance = new_balance
        acc.save(update_fields=["balance", "updated_at"])

        txn = TransactionHistory.objects.create(
            account=acc,
            amount=amount,
            balance_after=new_balance,
            description=description or "",
            io_type=io_type,
            method=method,
            created_at=when or timezone.now(),
        )
        return txn


class TransactionHistory(models.Model):
    """
    transaction_history 테이블
    - 계좌(FK), 거래금액, 거래 후 잔액, 설명, 입출금 타입, 거래 타입, 거래일시
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=18, decimal_places=2)         # 양수
    balance_after = models.DecimalField(max_digits=18, decimal_places=2)  # 거래 직후 잔액
    description = models.CharField(max_length=255, blank=True, default="")
    io_type = models.CharField(max_length=10, choices=TRANSACTION_IO)
    method = models.CharField(max_length=16, choices=TRANSACTION_METHOD, default="TRANSFER")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "transaction_history"
        indexes = [
            models.Index(fields=["account", "-created_at"], name="idx_txn_acct_created"),
            models.Index(fields=["account", "io_type"], name="idx_txn_acct_io"),
        ]
        ordering = ("-created_at",)

    def __str__(self):
        sign = "+" if self.io_type == "DEPOSIT" else "-"
        return f"{self.account_id} {sign}{self.amount} @ {self.created_at:%F %T}"
