# apps/banking/views_accounts.py
from rest_framework import viewsets, permissions, mixins
from .models import Account
from .serializers_accounts import AccountSerializer, AccountCreateSerializer

class IsOwnerOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id

class AccountViewSet(mixins.CreateModelMixin,
                     mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.DestroyModelMixin,   # 삭제만 허용
                     viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    queryset = Account.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        return AccountCreateSerializer if self.action == "create" else AccountSerializer
