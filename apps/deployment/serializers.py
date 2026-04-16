from rest_framework import serializers

from apps.packages.models import PackageArtifact

from .models import DeploymentTask
from .user_edit import parse_user_edit_block

_VALID_ACTIONS = {
    DeploymentTask.PRECHECK_INSTALL,
    DeploymentTask.PRECHECK_UPGRADE,
    DeploymentTask.INSTALL,
    DeploymentTask.UPGRADE,
    DeploymentTask.UNINSTALL_ALL,
}


class DeploymentTaskSerializer(serializers.ModelSerializer):
    host_name = serializers.CharField(source="host.name", read_only=True)
    host_node2_name = serializers.CharField(source="host_node2.name", read_only=True)
    host_node3_name = serializers.CharField(source="host_node3.name", read_only=True)
    created_by_username = serializers.SerializerMethodField()
    outcome_label = serializers.SerializerMethodField()
    package_release_name = serializers.CharField(
        source="package_release.name", read_only=True, allow_null=True
    )

    class Meta:
        model = DeploymentTask
        fields = (
            "id",
            "host",
            "host_name",
            "host_node2",
            "host_node2_name",
            "host_node3",
            "host_node3_name",
            "deploy_mode",
            "user_edit_content",
            "remote_user_edit_path",
            "package_release",
            "package_release_name",
            "package_artifact_ids",
            "skip_package_sync",
            "action",
            "target",
            "status",
            "exit_code",
            "error_message",
            "outcome_label",
            "created_by_username",
            "created_at",
            "started_at",
            "finished_at",
        )
        read_only_fields = (
            "id",
            "status",
            "exit_code",
            "error_message",
            "created_at",
            "started_at",
            "finished_at",
            "host_name",
            "host_node2_name",
            "host_node3_name",
            "remote_user_edit_path",
            "created_by_username",
            "outcome_label",
            "package_release_name",
        )

    def get_created_by_username(self, obj):
        u = getattr(obj, "created_by", None)
        return getattr(u, "username", None) or ""

    def get_outcome_label(self, obj):
        s = obj.status
        if s == DeploymentTask.STATUS_SUCCESS:
            return "成功"
        if s == DeploymentTask.STATUS_FAILED:
            return "失败"
        if s == DeploymentTask.STATUS_CANCELLED:
            return "已取消"
        if s == DeploymentTask.STATUS_RUNNING:
            return "执行中"
        if s == DeploymentTask.STATUS_PENDING:
            return "待执行"
        return s or "—"


class DeploymentTaskCreateSerializer(serializers.ModelSerializer):
    package_artifact_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True, default=list
    )

    class Meta:
        model = DeploymentTask
        fields = (
            "host",
            "host_node2",
            "host_node3",
            "deploy_mode",
            "user_edit_content",
            "action",
            "target",
            "package_release",
            "package_artifact_ids",
            "skip_package_sync",
        )

    def validate(self, attrs):
        if attrs.get("action") not in _VALID_ACTIONS:
            raise serializers.ValidationError({"action": "不支持的操作类型"})

        mode = attrs.get("deploy_mode") or DeploymentTask.MODE_SINGLE
        if mode not in (DeploymentTask.MODE_SINGLE, DeploymentTask.MODE_TRIPLE):
            raise serializers.ValidationError({"deploy_mode": "无效的部署形态"})

        content = (attrs.get("user_edit_content") or "").strip()
        if not content:
            raise serializers.ValidationError({"user_edit_content": "请填写 user_edit 配置文件内容"})
        _, err = parse_user_edit_block(content)
        if err:
            raise serializers.ValidationError({"user_edit_content": err})

        h1 = attrs.get("host")
        h2 = attrs.get("host_node2")
        h3 = attrs.get("host_node3")

        if mode == DeploymentTask.MODE_SINGLE:
            if h2 is not None or h3 is not None:
                raise serializers.ValidationError(
                    {"host_node2": "单节点部署请勿选择节点 2 / 节点 3"}
                )
        else:
            if h1 is None:
                raise serializers.ValidationError({"host": "请选择节点 1（执行机）"})
            chosen = [x.id for x in (h1, h2, h3) if x is not None]
            if len(chosen) != len(set(chosen)):
                raise serializers.ValidationError({"host": "所选主机不能重复"})

        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            for label, hx in (("host", h1), ("host_node2", h2), ("host_node3", h3)):
                if hx is None:
                    continue
                if hx.created_by_id and hx.created_by_id != user.id:
                    raise serializers.ValidationError({label: "无权使用该主机"})

        rel = attrs.get("package_release")
        skip = bool(attrs.get("skip_package_sync"))
        raw_ids = attrs.get("package_artifact_ids") or []
        ids = []
        if isinstance(raw_ids, list):
            for x in raw_ids:
                if x is None:
                    continue
                try:
                    ids.append(int(x))
                except (TypeError, ValueError):
                    raise serializers.ValidationError(
                        {"package_artifact_ids": "安装包 ID 须为整数: %r" % (x,)}
                    )
        attrs["package_artifact_ids"] = ids

        if skip:
            attrs["package_release"] = None
            attrs["package_artifact_ids"] = []
        elif rel is not None:
            if user and user.is_authenticated and not user.is_staff:
                if rel.created_by_id and rel.created_by_id != user.id:
                    raise serializers.ValidationError(
                        {"package_release": "无权使用该安装包版本"}
                    )
            if not ids:
                raise serializers.ValidationError(
                    {"package_artifact_ids": "请选择要下发的安装包，或勾选跳过安装包同步"}
                )
            qs = PackageArtifact.objects.filter(release=rel, pk__in=ids)
            if qs.count() != len(set(ids)):
                raise serializers.ValidationError(
                    {"package_artifact_ids": "存在无效的安装包 ID 或所选包不属于该版本"}
                )
        else:
            if ids:
                raise serializers.ValidationError(
                    {"package_release": "已选择安装包时必须指定安装包版本"}
                )
            attrs["package_artifact_ids"] = []

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        mode = validated_data.get("deploy_mode")
        if mode == DeploymentTask.MODE_SINGLE:
            validated_data["host_node2"] = None
            validated_data["host_node3"] = None
        if validated_data.get("skip_package_sync"):
            validated_data["package_release"] = None
            validated_data["package_artifact_ids"] = []
        return super().create(validated_data)
