from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_workflowtemplate_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workitem",
            name="item_code",
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
