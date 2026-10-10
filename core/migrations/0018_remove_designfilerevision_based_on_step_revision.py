from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_revision_cross_step_link"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="designfilerevision",
            name="based_on_step_revision",
        ),
    ]
