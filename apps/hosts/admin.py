from django.contrib import admin

from .models import Host


@admin.register(Host)
class HostAdmin(admin.ModelAdmin):
    list_display = ("name", "hostname", "port", "username", "auth_method", "created_at")
    search_fields = ("name", "hostname")
