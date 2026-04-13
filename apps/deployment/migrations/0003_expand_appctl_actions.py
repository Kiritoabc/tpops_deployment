# Generated manually

from django.db import migrations, models


def forwards_map_actions(apps, schema_editor):
    DeploymentTask = apps.get_model("deployment", "DeploymentTask")
    DeploymentTask.objects.filter(action="precheck").update(action="precheck_install")


def noop_reverse(apps, schema_editor):
    DeploymentTask = apps.get_model("deployment", "DeploymentTask")
    DeploymentTask.objects.filter(action="precheck_install").update(action="precheck")


class Migration(migrations.Migration):

    dependencies = [
        ("deployment", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(forwards_map_actions, noop_reverse),
        migrations.AlterField(
            model_name="deploymenttask",
            name="action",
            field=models.CharField(
                choices=[
                    ("precheck_install", "安装前置检查 (precheck install)"),
                    ("precheck_upgrade", "升级前置检查 (precheck upgrade)"),
                    ("install", "安装 (install)"),
                    ("upgrade", "升级 (upgrade)"),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="deploymenttask",
            name="target",
            field=models.CharField(
                blank=True,
                default="gaussdb",
                help_text="precheck install|upgrade 时传入的组件名，如 gaussdb；纯 install/upgrade 可留空",
                max_length=64,
            ),
        ),
    ]
