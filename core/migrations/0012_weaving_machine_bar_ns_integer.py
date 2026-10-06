from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_weaving_machine"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="weavingmachinebar",
            name="ns",
        ),
        migrations.AddField(
            model_name="weavingmachinebar",
            name="ns",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
