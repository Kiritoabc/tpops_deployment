from django.contrib import admin

from .models import DeploymentTask


@admin.register(DeploymentTask)
class DeploymentTaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "host",
        "deploy_mode",
        "action",
        "target",
        "remote_user_edit_path",
        "status",
        "exit_code",
        "created_at",
    )
    list_filter = ("action", "status", "deploy_mode")
    raw_id_fields = ("host", "host_node2", "host_node3", "created_by")
