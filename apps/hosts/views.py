from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Host
from .serializers import HostSerializer, host_ssh_secret
from .ssh_client import test_ssh_connection


class HostViewSet(viewsets.ModelViewSet):
    queryset = Host.objects.all()
    serializer_class = HostSerializer

    def get_queryset(self):
        qs = super().get_queryset().select_related("created_by")
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        # 管理员可见全部；普通用户可见自己创建的 + 历史上未绑定属主的主机（created_by 为空）
        if user.is_staff:
            return qs
        return qs.filter(Q(created_by=user) | Q(created_by__isnull=True))

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        host = self.get_object()
        secret = host_ssh_secret(host)
        if not secret:
            return Response(
                {"ok": False, "message": "未配置 SSH 密码或私钥"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ok, message = test_ssh_connection(
            host.hostname,
            host.port,
            host.username,
            host.auth_method,
            secret,
        )
        return Response({"ok": ok, "message": message})
