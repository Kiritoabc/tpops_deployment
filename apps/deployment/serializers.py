from rest_framework import serializers

from .models import DeploymentTask

_VALID_ACTIONS = {
    DeploymentTask.PRECHECK_INSTALL,
    DeploymentTask.PRECHECK_UPGRADE,
    DeploymentTask.INSTALL,
    DeploymentTask.UPGRADE,
}


class DeploymentTaskSerializer(serializers.ModelSerializer):
    host_name = serializers.CharField(source="host.name", read_only=True)

    class Meta:
        model = DeploymentTask
        fields = (
            "id",
            "host",
            "host_name",
            "action",
            "target",
            "status",
            "exit_code",
            "error_message",
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
        )


class DeploymentTaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeploymentTask
        fields = ("host", "action", "target")

    def validate(self, attrs):
        if attrs.get("action") not in _VALID_ACTIONS:
            raise serializers.ValidationError({"action": "不支持的操作类型"})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)
