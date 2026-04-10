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
        qs = super().get_queryset()
        if self.request.user.is_authenticated:
            return qs.filter(created_by=self.request.user)
        return qs.none()

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
