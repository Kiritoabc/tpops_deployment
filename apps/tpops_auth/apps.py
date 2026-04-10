from django.apps import AppConfig


class TpopsAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tpops_auth"
    label = "tpops_auth"
    verbose_name = "认证模块"
