# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("deployment", "0008_uninstall_all_action"),
        ("packages", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="deploymenttask",
            name="package_release",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="deployment_tasks",
                to="packages.packagerelease",
                verbose_name="安装包版本",
            ),
        ),
        migrations.AddField(
            model_name="deploymenttask",
            name="package_artifact_ids",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="来自所选版本的 Artifact 主键列表；空且未勾选跳过时不下发",
                verbose_name="下发的安装包 ID 列表",
            ),
        ),
        migrations.AddField(
            model_name="deploymenttask",
            name="skip_package_sync",
            field=models.BooleanField(
                default=False,
                help_text="为 True 时不向远端 pkgs 上传（使用环境已有包）",
                verbose_name="跳过安装包同步",
            ),
        ),
    ]
