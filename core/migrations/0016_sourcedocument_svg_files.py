from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_color_svg_pixel_groups"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="sourcedocument",
            name="svg_file",
        ),
        migrations.AddField(
            model_name="sourcedocument",
            name="svg_files",
            field=models.ManyToManyField(
                blank=True,
                related_name="source_document_svgs",
                to="core.fileobject",
            ),
        ),
    ]
