from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_rename_weaving_machine_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="colordefinition",
            name="is_svg",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="colordefinition",
            name="is_pixel",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="usercolorpreference",
            name="is_svg",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="usercolorpreference",
            name="is_pixel",
            field=models.BooleanField(default=True),
        ),
        migrations.RemoveConstraint(
            model_name="usercolorpreference",
            name="uq_user_color_code",
        ),
        migrations.AddConstraint(
            model_name="usercolorpreference",
            constraint=models.UniqueConstraint(
                fields=("user", "code", "is_svg", "is_pixel"),
                name="uq_user_color_code_group",
            ),
        ),
    ]
