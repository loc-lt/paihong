import uuid
from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_design_file_draft"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeavingMachine",
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
                ("name", models.CharField(max_length=100, unique=True)),
                ("max_bars", models.PositiveIntegerField(default=0)),
            ],
            options={
                "db_table": "weaving_machine",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="WeavingMachineSpec",
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
                (
                    "needles_per_inch",
                    models.DecimalField(decimal_places=2, max_digits=8),
                ),
                ("width", models.DecimalField(decimal_places=2, max_digits=8)),
                (
                    "machine",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="specs",
                        to="core.weavingmachine",
                    ),
                ),
            ],
            options={
                "db_table": "weaving_machine_spec",
                "ordering": ["needles_per_inch", "width"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("machine", "needles_per_inch", "width"),
                        name="uq_weaving_machine_spec",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="WeavingMachineBar",
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
                ("bar_no", models.PositiveIntegerField()),
                ("bar_code", models.CharField(max_length=20)),
                (
                    "zul_max_kg",
                    models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=8),
                ),
                ("max_versatzsprung", models.IntegerField(default=0)),
                ("max_ueberlegungssprung", models.IntegerField(default=0)),
                ("ns", models.BooleanField(default=False)),
                (
                    "machine",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bars",
                        to="core.weavingmachine",
                    ),
                ),
            ],
            options={
                "db_table": "weaving_machine_bar",
                "ordering": ["bar_no"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("machine", "bar_no"),
                        name="uq_weaving_machine_bar_no",
                    )
                ],
            },
        ),
    ]
