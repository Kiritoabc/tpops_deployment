from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("deployment", "0007_install_action_rename"),
    ]

    operations = [
        migrations.AlterField(
            model_name="deploymenttask",
            name="action",
            field=models.CharField(
                choices=[
                    ("precheck_install", "安装前置检查 (precheck install)"),
                    ("precheck_upgrade", "升级前置检查 (precheck upgrade)"),
                    ("install", "安装操作 (install)"),
                    ("upgrade", "升级操作 (upgrade)"),
                    ("uninstall_all", "卸载全部 (uninstall_all)"),
                ],
                max_length=32,
            ),
        ),
    ]
