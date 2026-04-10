from django.contrib import admin

from .models import DeploymentTask


@admin.register(DeploymentTask)
class DeploymentTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "host", "action", "target", "status", "exit_code", "created_at")
    list_filter = ("action", "status")
