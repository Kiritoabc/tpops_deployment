from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "is_active",
        "last_login",
        "last_login_ip",
    )
    list_filter = ("is_active", "role")
    search_fields = ("username", "email", "first_name", "last_name")

    fieldsets = BaseUserAdmin.fieldsets + (
        ("额外信息", {"fields": ("role", "last_login_ip")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("额外信息", {"fields": ("role",)}),
    )
