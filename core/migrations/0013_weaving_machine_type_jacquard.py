from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_weaving_machine_bar_ns_integer"),
    ]

    operations = [
        migrations.AddField(
            model_name="weavingmachine",
            name="machine_type",
            field=models.CharField(
                choices=[("Single", "Single"), ("Double", "Double")],
                default="Single",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="weavingmachine",
            name="jacquard",
            field=models.PositiveSmallIntegerField(
                choices=[(1, "1"), (2, "2")],
                default=1,
            ),
        ),
    ]
