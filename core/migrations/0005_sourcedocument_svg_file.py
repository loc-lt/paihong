import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_explicit_model_field_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourcedocument",
            name="svg_file",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_document_svgs",
                to="core.fileobject",
            ),
        ),
    ]
