from django.conf import settings
from django.db import models


class DeploymentTask(models.Model):
    PRECHECK = "precheck"
    INSTALL = "install"
    ACTION_CHOICES = [
        (PRECHECK, "预检查"),
        (INSTALL, "安装"),
    ]

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "待执行"),
        (STATUS_RUNNING, "执行中"),
        (STATUS_SUCCESS, "成功"),
        (STATUS_FAILED, "失败"),
        (STATUS_CANCELLED, "已取消"),
    ]

    host = models.ForeignKey(
        "hosts.Host",
        on_delete=models.CASCADE,
        related_name="deployment_tasks",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    target = models.CharField(
        max_length=64,
        default="gaussdb",
        help_text="appctl.sh 目标，例如 gaussdb",
    )
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    exit_code = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deployment_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "部署任务"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.get_action_display()} {self.target} ({self.status})"
