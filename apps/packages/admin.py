from django.contrib import admin

from .models import PackageArtifact, PackageRelease


@admin.register(PackageRelease)
class PackageReleaseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_by", "created_at")
    search_fields = ("name",)


@admin.register(PackageArtifact)
class PackageArtifactAdmin(admin.ModelAdmin):
    list_display = ("id", "release", "remote_basename", "size", "uploaded_at")
    list_filter = ("release",)
