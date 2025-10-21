# apps/banking/views_transactions.py
from rest_framework import permissions, status, mixins, viewsets
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.db.models import Q
from .models import Account, TransactionHistory
from .serializers_transactions import (
    TransactionCreateSerializer,
    TransactionSerializer,
    TransactionUpdateSerializer,
)
from rest_framework.request import Request

class IsOwnerOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # TransactionHistory의 소유자는 account.user
        return getattr(obj, "account", None) and obj.account.user_id == request.user.id


class TransactionViewSet(mixins.CreateModelMixin,
                         mixins.ListModelMixin,
                         mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    queryset = TransactionHistory.objects.select_related("account").all()
    lookup_field = "id"
    request: Request

    def get_queryset(self):

        user = self.request.user
        qs = self.queryset.filter(account__user=user).order_by("-created_at")


        # -------- 필터링 --------
        io_type = self.request.query_params.get("io_type")            # DEPOSIT / WITHDRAW
        method = self.request.query_params.get("method")              # CASH/TRANSFER/AUTO/CARD/ETC
        account_id = self.request.query_params.get("account_id")
        min_amount = self.request.query_params.get("min_amount")
        max_amount = self.request.query_params.get("max_amount")
        date_from = self.request.query_params.get("from")             # ISO(예: 2025-10-01T00:00:00Z)
        date_to = self.request.query_params.get("to")

        if io_type:
            qs = qs.filter(io_type=io_type)
        if method:
            qs = qs.filter(method=method)
        if account_id:
            qs = qs.filter(account_id=account_id)
        if min_amount:
            qs = qs.filter(amount__gte=min_amount)
        if max_amount:
            qs = qs.filter(amount__lte=max_amount)
        if date_from:
            dt = parse_datetime(date_from) or date_from
            qs = qs.filter(created_at__gte=dt)
        if date_to:
            dt = parse_datetime(date_to) or date_to
            qs = qs.filter(created_at__lte=dt)

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return TransactionCreateSerializer
        if self.action in ("update", "partial_update"):
            return TransactionUpdateSerializer
        return TransactionSerializer

    def create(self, request, *args, **kwargs):
        s = TransactionCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data

        # 소유권 검증
        account = get_object_or_404(Account, id=data["account_id"], user=request.user)

        # 모델 메서드로 안전 처리(잔액 업데이트 + 거래 생성)
        txn = account.apply_transaction(
            amount=data["amount"],
            io_type=data["io_type"],
            method=data["method"],
            description=data.get("description", ""),
        )
        out = TransactionSerializer(txn)
        return Response(out.data, status=status.HTTP_201_CREATED)
