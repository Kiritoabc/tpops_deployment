from django.db import migrations, models


def forwards(apps, schema_editor):
    DeploymentTask = apps.get_model("deployment", "DeploymentTask")
    DeploymentTask.objects.filter(action="installl").update(action="install")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("deployment", "0006_four_actions_installl"),
    ]

    operations = [
        migrations.RunPython(forwards, noop),
        migrations.AlterField(
            model_name="deploymenttask",
            name="action",
            field=models.CharField(
                choices=[
                    ("precheck_install", "安装前置检查 (precheck install)"),
                    ("precheck_upgrade", "升级前置检查 (precheck upgrade)"),
                    ("install", "安装操作 (install)"),
                    ("upgrade", "升级操作 (upgrade)"),
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
                help_text="precheck install / precheck upgrade 必填组件名（如 gaussdb）；install / upgrade 按现场脚本可选填",
                max_length=64,
            ),
        ),
    ]
