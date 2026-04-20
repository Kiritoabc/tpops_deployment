from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.deployment.user_edit import parse_user_edit_block

from .models import Host
from .serializers import HostSerializer, host_ssh_secret
from .ssh_client import (
    remote_cat_file,
    resolve_user_edit_conf_path,
    test_ssh_connection,
)


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

    @action(detail=True, methods=["get"], url_path="fetch_user_edit")
    def fetch_user_edit(self, request, pk=None):
        """
        从执行机读取已存在的 user_edit_file.conf（与部署任务相同的探测路径），
        供向导中「使用远程配置」填入表单；内容须能通过 [user_edit] 解析校验。
        """
        host = self.get_object()
        secret = host_ssh_secret(host)
        if not secret:
            return Response(
                {"detail": "该主机未配置 SSH 密码或私钥，无法读取远程文件"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        root = (host.docker_service_root or "").strip()
        path, perr = resolve_user_edit_conf_path(
            host.hostname,
            host.port,
            host.username,
            host.auth_method,
            secret,
            root,
            timeout=60,
        )
        if not path:
            return Response(
                {"detail": perr or "未找到远程 user_edit_file.conf"},
                status=status.HTTP_404_NOT_FOUND,
            )
        raw, _code = remote_cat_file(
            host.hostname,
            host.port,
            host.username,
            host.auth_method,
            secret,
            path,
            timeout=60,
        )
        text = (raw or "").replace("\r\n", "\n")
        if not text.strip():
            return Response(
                {"detail": "远程文件存在但内容为空"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        max_bytes = 512 * 1024
        if len(text.encode("utf-8")) > max_bytes:
            return Response(
                {"detail": "远程配置文件超过 512KB，请改用 SSH 手工编辑后缩小再试"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        _, parse_err = parse_user_edit_block(text)
        if parse_err:
            return Response(
                {"detail": "远程内容与平台校验不一致: %s" % parse_err},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"content": text, "remote_path": path})
