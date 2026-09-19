import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_sourcedocument_svg_file"),
    ]

    operations = [
        migrations.CreateModel(
            name="DesignWorkspace",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True, verbose_name="created")),
                ("modified", models.DateTimeField(auto_now=True, verbose_name="modified")),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("settings", models.JSONField(blank=True, default=dict)),
                (
                    "part_step",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="design_workspace",
                        to="core.partstep",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updated_design_workspaces",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "design_workspace",
            },
        ),
        migrations.CreateModel(
            name="DesignFile",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True, verbose_name="created")),
                ("modified", models.DateTimeField(auto_now=True, verbose_name="modified")),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("file_type", models.CharField(db_index=True, max_length=10)),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updated_design_files",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="files",
                        to="core.designworkspace",
                    ),
                ),
            ],
            options={
                "db_table": "design_file",
            },
        ),
        migrations.CreateModel(
            name="DesignFileRevision",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True, verbose_name="created")),
                ("modified", models.DateTimeField(auto_now=True, verbose_name="modified")),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("revision_no", models.PositiveIntegerField()),
                ("revision_type", models.IntegerField(db_index=True, default=2)),
                ("layers", models.JSONField(blank=True, default=list)),
                ("grid_width", models.PositiveIntegerField(default=0)),
                ("grid_height", models.PositiveIntegerField(default=0)),
                ("tile_manifest", models.JSONField(blank=True, default=dict)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_design_file_revisions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "design_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="revisions",
                        to="core.designfile",
                    ),
                ),
                (
                    "parent_revision",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="child_revisions",
                        to="core.designfilerevision",
                    ),
                ),
                (
                    "preview_file",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="design_file_previews",
                        to="core.fileobject",
                    ),
                ),
                (
                    "snapshot_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="design_file_snapshots",
                        to="core.fileobject",
                    ),
                ),
            ],
            options={
                "db_table": "design_file_revision",
                "ordering": ["-revision_no"],
            },
        ),
        migrations.AddField(
            model_name="designfile",
            name="latest_revision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="core.designfilerevision",
            ),
        ),
        migrations.AddField(
            model_name="designfile",
            name="official_revision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="core.designfilerevision",
            ),
        ),
        migrations.AddConstraint(
            model_name="designfile",
            constraint=models.UniqueConstraint(
                fields=("workspace", "file_type"),
                name="uq_design_file_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="designfilerevision",
            constraint=models.UniqueConstraint(
                fields=("design_file", "revision_no"),
                name="uq_design_file_revision_no",
            ),
        ),
        migrations.CreateModel(
            name="ColorDefinition",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True, verbose_name="created")),
                ("modified", models.DateTimeField(auto_now=True, verbose_name="modified")),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("code", models.PositiveSmallIntegerField(unique=True)),
                ("hex_value", models.CharField(max_length=7)),
                ("name", models.CharField(max_length=100)),
                ("default_order", models.PositiveSmallIntegerField(default=0)),
                ("is_system", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "color_definition",
                "ordering": ["default_order", "code"],
            },
        ),
        migrations.CreateModel(
            name="UserColorPreference",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True, verbose_name="created")),
                ("modified", models.DateTimeField(auto_now=True, verbose_name="modified")),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("custom_hex", models.CharField(blank=True, default="", max_length=7)),
                ("custom_name", models.CharField(blank=True, default="", max_length=100)),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "color_definition",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_preferences",
                        to="core.colordefinition",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="color_preferences",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "user_color_preference",
                "ordering": ["display_order", "created"],
            },
        ),
        migrations.AddConstraint(
            model_name="usercolorpreference",
            constraint=models.UniqueConstraint(
                condition=models.Q(color_definition__isnull=False),
                fields=("user", "color_definition"),
                name="uq_user_color_definition",
            ),
        ),
    ]
