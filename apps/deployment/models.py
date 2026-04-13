from django.conf import settings
from django.db import models


class DeploymentTask(models.Model):
    """远程：precheck install / precheck upgrade / install / upgrade（sh appctl.sh）"""

    PRECHECK_INSTALL = "precheck_install"
    PRECHECK_UPGRADE = "precheck_upgrade"
    INSTALL = "install"
    UPGRADE = "upgrade"

    ACTION_CHOICES = [
        (PRECHECK_INSTALL, "安装前置检查 (precheck install)"),
        (PRECHECK_UPGRADE, "升级前置检查 (precheck upgrade)"),
        (INSTALL, "安装操作 (install)"),
        (UPGRADE, "升级操作 (upgrade)"),
    ]

    MODE_SINGLE = "single"
    MODE_TRIPLE = "triple"
    DEPLOY_MODE_CHOICES = [
        (MODE_SINGLE, "单节点"),
        (MODE_TRIPLE, "三节点"),
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
        help_text="precheck install / precheck upgrade 必填组件名（如 gaussdb）；install / upgrade 按现场脚本可选填",
    )
    deploy_mode = models.CharField(
        max_length=16,
        choices=DEPLOY_MODE_CHOICES,
        default=MODE_SINGLE,
        verbose_name="部署形态",
    )
    host_node2 = models.ForeignKey(
        "hosts.Host",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deployment_tasks_as_node2",
        verbose_name="节点2（仅三节点）",
    )
    host_node3 = models.ForeignKey(
        "hosts.Host",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deployment_tasks_as_node3",
        verbose_name="节点3（仅三节点）",
    )
    user_edit_content = models.TextField(
        verbose_name="user_edit 配置内容",
        help_text="将写入远程 user_edit_file.conf（覆盖前会先解析 [user_edit]）",
    )
    remote_user_edit_path = models.CharField(
        max_length=512,
        blank=True,
        verbose_name="实际写入的远程路径",
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
