# apps/banking/views_accounts.py
from rest_framework import viewsets, permissions, mixins, status
from rest_framework.response import Response

from .models import Account
from .serializers_accounts import AccountSerializer, AccountCreateSerializer


class IsOwnerOnly(permissions.BasePermission):
    """객체 단위 권한: 소유자만 허용"""
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id


class AccountViewSet(mixins.CreateModelMixin,
                     mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.DestroyModelMixin,   # 삭제 허용
                     viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOnly]
    queryset = Account.objects.select_related("user").all()
    lookup_field = "id"

    def get_queryset(self):
        # 목록/조회 모두 내 계좌만
        return self.queryset.filter(user=self.request.user).order_by("-created_at")

    def get_serializer_class(self):
        # 생성 시에는 작성용 시리얼라이저, 그 외는 조회용
        return AccountCreateSerializer if self.action == "create" else AccountSerializer

    def create(self, request, *args, **kwargs):
        """
        생성은 AccountCreateSerializer로 검증/저장하고,
        응답은 AccountSerializer로 직렬화하여 id 포함 반환.
        """
        write_ser = AccountCreateSerializer(data=request.data, context={"request": request})
        write_ser.is_valid(raise_exception=True)
        account = write_ser.save()  # create()에서 user를 request.user로 바인딩

        read_ser = AccountSerializer(account, context={"request": request})
        headers = self.get_success_headers(read_ser.data)
        return Response(read_ser.data, status=status.HTTP_201_CREATED, headers=headers)
