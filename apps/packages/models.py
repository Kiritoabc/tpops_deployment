import os
import re

from django.conf import settings
from django.db import models


def _safe_remote_basename(name: str) -> str:
    base = os.path.basename((name or "").strip() or "unnamed")
    base = re.sub(r"[^A-Za-z0-9._+\-]", "_", base)
    if not base or base in (".", ".."):
        base = "unnamed"
    return base[:255]


class PackageRelease(models.Model):
    """TPOPS 安装包版本（介质分组）。"""

    name = models.CharField(max_length=128, verbose_name="版本名称")
    description = models.TextField(blank=True, verbose_name="说明")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="package_releases",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "安装包版本"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class PackageArtifact(models.Model):
    """某版本下的单个安装包文件；下发到远端 <部署根>/pkgs/<remote_basename>。"""

    release = models.ForeignKey(
        PackageRelease,
        on_delete=models.CASCADE,
        related_name="artifacts",
    )
    file = models.FileField(upload_to="packages/%Y/%m/", verbose_name="文件")
    original_name = models.CharField(max_length=255, verbose_name="原始文件名")
    remote_basename = models.CharField(max_length=255, verbose_name="远端文件名")
    size = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="package_artifacts",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "安装包文件"
        verbose_name_plural = verbose_name
        unique_together = [("release", "remote_basename")]

    def __str__(self):
        return "%s / %s" % (self.release.name, self.remote_basename)

    def save(self, *args, **kwargs):
        if not self.remote_basename:
            self.remote_basename = _safe_remote_basename(self.original_name)
        super().save(*args, **kwargs)
