from django.conf import settings
from django.db import models


class Host(models.Model):
    AUTH_KEY = "key"
    AUTH_PASSWORD = "password"
    AUTH_CHOICES = [
        (AUTH_KEY, "密钥"),
        (AUTH_PASSWORD, "密码"),
    ]

    name = models.CharField(max_length=128, verbose_name="名称")
    hostname = models.CharField(max_length=255, verbose_name="地址")
    port = models.PositiveIntegerField(default=22, verbose_name="SSH 端口")
    username = models.CharField(max_length=64, verbose_name="SSH 用户")
    auth_method = models.CharField(
        max_length=16, choices=AUTH_CHOICES, default=AUTH_PASSWORD
    )
    # Stored encrypted at rest (see hosts.crypto)
    credential = models.TextField(blank=True, verbose_name="凭证密文")
    docker_service_root = models.CharField(
        max_length=512,
        blank=True,
        verbose_name="部署根目录",
        help_text="远程主机上 appctl.sh 所在目录，例如 /data/docker-service",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hosts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "服务器"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.hostname})"
