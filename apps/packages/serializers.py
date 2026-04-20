from rest_framework import serializers

from .models import PackageArtifact, PackageRelease, _safe_remote_basename


class PackageArtifactSerializer(serializers.ModelSerializer):
    release_name = serializers.CharField(source="release.name", read_only=True)
    uploaded_by_username = serializers.SerializerMethodField()

    class Meta:
        model = PackageArtifact
        fields = (
            "id",
            "release",
            "release_name",
            "file",
            "original_name",
            "remote_basename",
            "size",
            "sha256",
            "uploaded_by_username",
            "uploaded_at",
        )
        read_only_fields = (
            "id",
            "file",
            "original_name",
            "size",
            "sha256",
            "uploaded_at",
            "release_name",
            "uploaded_by_username",
        )

    def get_uploaded_by_username(self, obj):
        u = getattr(obj, "uploaded_by", None)
        return getattr(u, "username", None) or ""


class PackageArtifactCreateSerializer(serializers.Serializer):
    """
    multipart：release + file；remote_basename 可选（缺省由上传文件名推导）。

    使用显式 Serializer 而非 ModelSerializer，避免模型上 CharField 无 blank=True
    时被 DRF 误判为「必填」——浏览器原生 multipart 常不传该字段。
    """

    release = serializers.PrimaryKeyRelatedField(queryset=PackageRelease.objects.all())
    file = serializers.FileField()
    remote_basename = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )

    def validate(self, attrs):
        f = attrs.get("file")
        if not f:
            raise serializers.ValidationError({"file": "请选择文件"})
        orig = getattr(f, "name", "") or "unnamed"
        attrs["original_name"] = orig
        rb = (attrs.get("remote_basename") or "").strip()
        attrs["remote_basename"] = _safe_remote_basename(rb) if rb else _safe_remote_basename(orig)
        return attrs

    def create(self, validated_data):
        import hashlib

        f = validated_data["file"]
        orig = validated_data["original_name"]
        rb = validated_data["remote_basename"]
        release = validated_data["release"]
        h = hashlib.sha256()
        n = 0
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
            n += len(chunk)
        f.seek(0)
        sha = h.hexdigest()
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None

        existing = PackageArtifact.objects.filter(release=release, remote_basename=rb).first()
        if existing:
            if existing.file:
                existing.file.delete(save=False)
            existing.file = f
            existing.original_name = orig
            existing.size = n
            existing.sha256 = sha
            existing.uploaded_by = user
            existing.save()
            return existing

        return PackageArtifact.objects.create(
            release=release,
            file=f,
            original_name=orig,
            remote_basename=rb,
            size=n,
            sha256=sha,
            uploaded_by=user,
        )


class PackageReleaseSerializer(serializers.ModelSerializer):
    created_by_username = serializers.SerializerMethodField()
    artifact_count = serializers.SerializerMethodField()

    class Meta:
        model = PackageRelease
        fields = (
            "id",
            "name",
            "description",
            "created_by_username",
            "created_at",
            "updated_at",
            "artifact_count",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "created_by_username",
            "artifact_count",
        )

    def get_created_by_username(self, obj):
        u = getattr(obj, "created_by", None)
        return getattr(u, "username", None) or ""

    def get_artifact_count(self, obj):
        return obj.artifacts.count()


class PackageReleaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageRelease
        fields = ("name", "description")

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)
