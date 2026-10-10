import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_sourcedocument_svg_files"),
    ]

    operations = [
        migrations.AddField(
            model_name="steprevision",
            name="based_on_revision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="based_revisions",
                to="core.steprevision",
            ),
        ),
        migrations.AddField(
            model_name="designfilerevision",
            name="based_on_step_revision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="design_file_revisions",
                to="core.steprevision",
            ),
        ),
    ]
