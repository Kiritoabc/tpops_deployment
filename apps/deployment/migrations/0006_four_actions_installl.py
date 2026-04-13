# Map legacy action values to the four supported types

from django.db import migrations, models


def forwards(apps, schema_editor):
    DeploymentTask = apps.get_model("deployment", "DeploymentTask")
    DeploymentTask.objects.filter(action="install").update(action="installl")
    # 独立 precheck 合并为安装前置形态（目标参数沿用原 task）
    DeploymentTask.objects.filter(action="precheck").update(action="precheck_install")
    for legacy in ("uninstall_all", "rollback", "repair"):
        DeploymentTask.objects.filter(action=legacy).update(action="upgrade")


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("deployment", "0005_expand_actions_and_sh_appctl"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="deploymenttask",
            name="action",
            field=models.CharField(
                choices=[
                    ("precheck_install", "安装前置检查 (precheck install)"),
                    ("precheck_upgrade", "升级前置检查 (precheck upgrade)"),
                    ("installl", "安装操作 (installl)"),
                    ("upgrade", "升级操作 (upgrade)"),
                ],
                max_length=32,
            ),
        ),
    ]
