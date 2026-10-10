import uuid

import django.db.models.deletion
import django_extensions.db.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_alter_weavingmachine_created_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PartBranch",
            fields=[
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name="modified"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("number", models.PositiveIntegerField()),
                (
                    "head_revision",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="headed_branches",
                        to="core.steprevision",
                    ),
                ),
                (
                    "part",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="branches",
                        to="core.part",
                    ),
                ),
            ],
            options={
                "db_table": "part_branch",
                "ordering": ["number"],
            },
        ),
        migrations.AddConstraint(
            model_name="partbranch",
            constraint=models.UniqueConstraint(
                fields=("part", "number"),
                name="uq_part_branch_number",
            ),
        ),
        migrations.AddField(
            model_name="part",
            name="current_branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="core.partbranch",
            ),
        ),
    ]
