# Generated manually for TPOPS GaussDB package CPU/OS hints

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("deployment", "0009_deployment_package_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="deploymenttask",
            name="package_cpu_type",
            field=models.CharField(
                blank=True,
                default="",
                max_length=32,
                verbose_name="安装包 CPU 类型",
                help_text="用于校验 GaussDB 介质文件名中的 CPU 段（如 x86_64）",
            ),
        ),
        migrations.AddField(
            model_name="deploymenttask",
            name="package_os_type",
            field=models.CharField(
                blank=True,
                default="",
                max_length=32,
                verbose_name="安装包 OS 类型",
                help_text="用于校验 DBS-GaussDB-{OS}-Kernel_* 文件名中的 OS 段（如 openEuler）",
            ),
        ),
    ]
