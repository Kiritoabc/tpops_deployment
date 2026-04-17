from django.db import close_old_connections
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.hosts.serializers import host_ssh_secret

from .access import filter_deployment_tasks_for_user
from .models import DeploymentTask
from .runner import fetch_manifest_tree_for_task, run_task_async
from .serializers import DeploymentTaskCreateSerializer, DeploymentTaskSerializer


class DeploymentTaskViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        DeploymentTask.objects.select_related(
            "host", "host_node2", "host_node3", "created_by"
        ).all()
    )

    def get_serializer_class(self):
        if self.action == "create":
            return DeploymentTaskCreateSerializer
        return DeploymentTaskSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return filter_deployment_tasks_for_user(qs, self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        host = serializer.validated_data["host"]
        if host.created_by_id and host.created_by_id != request.user.id:
            return Response(
                {"detail": "无权使用该主机"},
                status=status.HTTP_403_FORBIDDEN,
            )
        task = serializer.save()
        run_task_async(task.id)
        return Response(
            DeploymentTaskSerializer(task, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def manifest_snapshot(self, request, pk=None):
        """
        单次 SSH 读取远程 manifest 并解析（与 WS manifest 消息同结构）。
        用于任务结束后再次打开详情页时刷新流水线与子任务 meta（含 finish_execute_time）。
        """
        close_old_connections()
        task = self.get_object()
        if task.action not in (DeploymentTask.INSTALL, DeploymentTask.UPGRADE):
            return Response(
                {
                    "detail": "当前任务类型不轮询 manifest",
                    "action": task.action,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        secret = host_ssh_secret(task.host)
        if not secret:
            return Response(
                {"detail": "执行机未配置 SSH 凭证，无法读取 manifest"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        tree, paths, details = fetch_manifest_tree_for_task(
            task.host, task, secret, None
        )
        if not tree:
            return Response(
                {
                    "detail": "未读取到有效 manifest YAML",
                    "paths": paths,
                    "poll_details": details,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(tree)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        # MVP: mark cancelled; running thread may still finish (document limitation)
        task = self.get_object()
        if task.status == DeploymentTask.STATUS_RUNNING:
            task.status = DeploymentTask.STATUS_CANCELLED
            task.save(update_fields=["status", "updated_at"])
            return Response({"detail": "已标记取消（运行中任务可能仍会结束）"})
        return Response(
            {"detail": "当前状态不可取消"},
            status=status.HTTP_400_BAD_REQUEST,
        )
