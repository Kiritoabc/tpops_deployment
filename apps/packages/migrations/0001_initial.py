# Generated manually for PackageRelease / PackageArtifact

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PackageRelease",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=128, verbose_name="版本名称")),
                ("description", models.TextField(blank=True, verbose_name="说明")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="package_releases",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "安装包版本",
                "verbose_name_plural": "安装包版本",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PackageArtifact",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        upload_to="packages/%Y/%m/",
                        verbose_name="文件",
                    ),
                ),
                (
                    "original_name",
                    models.CharField(max_length=255, verbose_name="原始文件名"),
                ),
                (
                    "remote_basename",
                    models.CharField(max_length=255, verbose_name="远端文件名"),
                ),
                ("size", models.BigIntegerField(default=0)),
                ("sha256", models.CharField(blank=True, max_length=64)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "release",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="artifacts",
                        to="packages.packagerelease",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="package_artifacts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "安装包文件",
                "verbose_name_plural": "安装包文件",
                "ordering": ["-uploaded_at"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="packageartifact",
            unique_together={("release", "remote_basename")},
        ),
    ]
