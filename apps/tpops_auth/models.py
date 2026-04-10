from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("admin", "系统管理员"),
        ("operator", "操作员"),
        ("viewer", "只读用户"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="viewer")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = "auth_user"
        verbose_name = "用户"
        verbose_name_plural = verbose_name
