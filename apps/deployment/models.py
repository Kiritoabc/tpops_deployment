from django.conf import settings
from django.db import models


class DeploymentTask(models.Model):
    """远程: cd <根目录> && bash appctl.sh <子命令>"""

    PRECHECK_INSTALL = "precheck_install"
    PRECHECK_UPGRADE = "precheck_upgrade"
    INSTALL = "install"
    UPGRADE = "upgrade"

    ACTION_CHOICES = [
        (PRECHECK_INSTALL, "安装前置检查 (precheck install)"),
        (PRECHECK_UPGRADE, "升级前置检查 (precheck upgrade)"),
        (INSTALL, "安装 (install)"),
        (UPGRADE, "升级 (upgrade)"),
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
        blank=True,
        help_text="precheck install|upgrade 时传入的组件名，如 gaussdb；纯 install/upgrade 可留空",
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
        return "%s %s (%s)" % (self.get_action_display(), self.target or "-", self.status)
