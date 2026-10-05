from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_colordefinition_display_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="designfile",
            name="name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="designfile",
            name="is_draft",
            field=models.BooleanField(default=False),
        ),
    ]
