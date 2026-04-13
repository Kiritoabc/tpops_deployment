from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import DeploymentTask
from .runner import run_task_async
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
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_staff:
            return qs
        return qs.filter(Q(created_by=user) | Q(created_by__isnull=True))

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
