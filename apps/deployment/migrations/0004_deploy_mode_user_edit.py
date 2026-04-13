# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hosts", "0004_manifest_path_hint"),
        ("deployment", "0003_expand_appctl_actions"),
    ]

    operations = [
        migrations.AddField(
            model_name="deploymenttask",
            name="deploy_mode",
            field=models.CharField(
                choices=[("single", "单节点"), ("triple", "三节点")],
                default="single",
                max_length=16,
                verbose_name="部署形态",
            ),
        ),
        migrations.AddField(
            model_name="deploymenttask",
            name="host_node2",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="deployment_tasks_as_node2",
                to="hosts.host",
                verbose_name="节点2（仅三节点）",
            ),
        ),
        migrations.AddField(
            model_name="deploymenttask",
            name="host_node3",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="deployment_tasks_as_node3",
                to="hosts.host",
                verbose_name="节点3（仅三节点）",
            ),
        ),
        migrations.AddField(
            model_name="deploymenttask",
            name="remote_user_edit_path",
            field=models.CharField(blank=True, max_length=512, verbose_name="实际写入的远程路径"),
        ),
        migrations.AddField(
            model_name="deploymenttask",
            name="user_edit_content",
            field=models.TextField(
                default="",
                help_text="将写入远程 user_edit_file.conf（覆盖前会先解析 [user_edit]）",
                verbose_name="user_edit 配置内容",
            ),
        ),
    ]
