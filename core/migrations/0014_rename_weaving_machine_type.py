from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_weaving_machine_type_jacquard"),
    ]

    operations = [
        migrations.RenameField(
            model_name="weavingmachine",
            old_name="machine_type",
            new_name="type",
        ),
    ]
