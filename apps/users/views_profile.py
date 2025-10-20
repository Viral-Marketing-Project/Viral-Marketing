# apps/users/views_profile.py
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers_profile import UserProfileSerializer

class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request):
        # 이 엔드포인트는 항상 "본인"만 대상으로 함
        return request.user

    def get(self, request):
        user = self.get_object(request)
        data = UserProfileSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)

    def put(self, request):
        """
        PUT: 전체 업데이트. 제공하지 않은 필드는 기본값/빈값으로 덮어쓰일 수 있음.
        """
        user = self.get_object(request)
        serializer = UserProfileSerializer(user, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        """
        PATCH: 부분 업데이트. 제공한 필드만 변경.
        """
        user = self.get_object(request)
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        user = self.get_object(request)
        user.delete()
        return Response({"detail": "Deleted successfully"}, status=status.HTTP_200_OK)
