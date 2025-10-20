import uuid
from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone
from django.conf import settings

# ---- 선택 1: 깨끗한 라벨을 가진 CHOICES (권장) ----
BANK_CODES = [
    ("KAKAO", "카카오뱅크"),
    ("KB",    "KB국민"),
    ("NH",    "농협"),
    ("IBK",   "기업"),
    ("SC",    "SC제일"),
    ("HANA",  "하나"),
    ("WOORI", "우리"),
    ("SHINHAN","신한"),
    ("ETC",   "기타"),
]

ACCOUNT_TYPES = [
    ("DEMAND",    "입출금통장"),    # 단순 입출금
    ("OVERDRAFT", "마이너스 통장"),
    ("SAVINGS",   "예·적금"),
    ("ETC",       "기타"),
]

TRANSACTION_IO = [
    ("DEPOSIT",  "입금"),
    ("WITHDRAW", "출금"),
]

TRANSACTION_METHOD = [
    ("CASH",      "현금"),
    ("TRANSFER",  "계좌 이체"),
    ("AUTO",      "자동 이체"),
    ("CARD",      "카드 결제"),
    ("ETC",       "기타"),
]

# ※ 네가 준 상수(BANK_CODES 등)를 그대로 쓰고 싶다면,
#    위 블록 대신 그 상수를 import 해서 CHOICES로 연결만 해주면 됨.

class Account(models.Model):
    """
    accounts 테이블 (요구필드 반영)
    - 유저 정보(FK)
    - 계좌번호
    - 은행 코드
    - 계좌 종류
    - 잔액
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accounts")
    account_number = models.CharField(max_length=32)  # 하이픈 제거 저장 권장
    bank_code = models.CharField(max_length=16, choices=BANK_CODES)
    account_type = models.CharField(max_length=16, choices=ACCOUNT_TYPES, default="DEMAND")
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts"
        # 전역 유니크(모든 사용자 전체에서 중복 금지) vs 유저별 유니크(같은 계좌를 다른 유저가 가질 수 있음)
        constraints = [
            # 전역 유니크가 필요하면 ↓만 남기고 아래 줄은 주석 처리
            # models.UniqueConstraint(fields=["bank_code", "account_number"], name="uq_bank_acct"),

            # 일반적으로는 "유저별 유니크"를 많이 사용
            models.UniqueConstraint(fields=["user", "bank_code", "account_number"], name="uq_user_bank_acct"),
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_acct_user_created"),
        ]

    def __str__(self):
        return f"{self.bank_code}-{self.account_number}"

    @transaction.atomic
    def apply_transaction(self, *, amount: Decimal, io_type: str, method: str, description: str = "", when=None):
        """
        동시성 안전 입출금 처리:
        - 자기 계좌 행을 select_for_update로 잠금
        - 잔액 갱신 + 거래 레코드 생성
        - amount는 양수(입금/출금은 io_type으로 구분)
        """
        acc = Account.objects.select_for_update().get(pk=self.pk)

        if io_type == "WITHDRAW" and acc.balance < amount:
            raise ValueError("잔액 부족")

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
    transaction_history 테이블 (요구필드 반영)
    - 계좌 정보(FK)
    - 거래 금액
    - 거래 후 잔액
    - 계좌 인자 내역(설명)
    - 입출금 타입(입금/출금)
    - 거래 타입(현금/이체/자동이체/카드 등)
    - 거래 일시
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=18, decimal_places=2)         # 양수
    balance_after = models.DecimalField(max_digits=18, decimal_places=2)  # 거래 직후 잔액
    description = models.CharField(max_length=255, blank=True, default="")    # 예: 올리브영, ATM입금, 오픈뱅킹 출금 등
    io_type = models.CharField(max_length=10, choices=TRANSACTION_IO)
    method = models.CharField(max_length=16, choices=TRANSACTION_METHOD, default="TRANSFER")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "transaction_history"
        indexes = [
            models.Index(fields=["account", "-created_at"], name="idx_txn_acct_created"),
            models.Index(fields=["account", "io_type"], name="idx_txn_acct_io"),
        ]

    def __str__(self):
        sign = "+" if self.io_type == "DEPOSIT" else "-"
        return f"{self.account_id} {sign}{self.amount} @ {self.created_at:%F %T}"
