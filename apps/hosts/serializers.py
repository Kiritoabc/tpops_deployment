from rest_framework import serializers

from .crypto import decrypt_secret, encrypt_secret
from .models import Host


class HostSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    private_key = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    has_credential = serializers.SerializerMethodField()
    owner_username = serializers.SerializerMethodField()

    class Meta:
        model = Host
        fields = (
            "id",
            "name",
            "hostname",
            "port",
            "username",
            "auth_method",
            "docker_service_root",
            "has_credential",
            "owner_username",
            "password",
            "private_key",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "has_credential",
            "owner_username",
        )

    def get_has_credential(self, obj):
        return bool((obj.credential or "").strip())

    def get_owner_username(self, obj):
        u = getattr(obj, "created_by", None)
        return getattr(u, "username", None) or ""

    def create(self, validated_data):
        password = validated_data.pop("password", "") or ""
        private_key = validated_data.pop("private_key", "") or ""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        if validated_data.get("auth_method") == Host.AUTH_KEY:
            secret = private_key
        else:
            secret = password
        validated_data["credential"] = encrypt_secret(secret) if secret else ""
        return super().create(validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        private_key = validated_data.pop("private_key", None)
        if password is not None or private_key is not None:
            if instance.auth_method == Host.AUTH_KEY:
                secret = private_key or ""
            else:
                secret = password or ""
            if secret:
                validated_data["credential"] = encrypt_secret(secret)
        return super().update(instance, validated_data)


class HostTestSerializer(serializers.Serializer):
    ok = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)


def host_ssh_secret(host: Host) -> str:
    return decrypt_secret(host.credential or "")
