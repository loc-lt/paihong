from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_user_custom_color_code"),
    ]

    operations = [
        migrations.RenameField(
            model_name="colordefinition",
            old_name="default_order",
            new_name="display_order",
        ),
        migrations.AlterModelOptions(
            name="colordefinition",
            options={"ordering": ["display_order", "code"]},
        ),
    ]
