from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import PackageArtifact, PackageRelease
from .serializers import (
    PackageArtifactCreateSerializer,
    PackageArtifactSerializer,
    PackageReleaseCreateSerializer,
    PackageReleaseSerializer,
)


class PackageReleaseViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = PackageRelease.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return PackageReleaseCreateSerializer
        return PackageReleaseSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(Q(created_by=user) | Q(created_by__isnull=True))


class PackageArtifactViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = PackageArtifact.objects.select_related("release", "uploaded_by")
    parser_classes = (MultiPartParser, FormParser)

    def get_serializer_class(self):
        if self.action == "create":
            return PackageArtifactCreateSerializer
        return PackageArtifactSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        rid = self.request.query_params.get("release")
        if rid:
            qs = qs.filter(release_id=rid)
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(
            Q(release__created_by=user) | Q(release__created_by__isnull=True)
        )

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        out = PackageArtifactSerializer(obj, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)
