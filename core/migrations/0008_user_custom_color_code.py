from django.db import migrations, models


def drop_system_overrides_and_assign_codes(apps, schema_editor):
    UserColorPreference = apps.get_model("core", "UserColorPreference")
    UserColorPreference.objects.exclude(color_definition_id=None).delete()
    UserColorPreference.objects.filter(custom_hex="").delete()

    used_by_user: dict = {}
    for pref in UserColorPreference.objects.order_by("created"):
        used = used_by_user.setdefault(pref.user_id, set())
        next_code = 1
        while next_code in used:
            next_code += 1
        pref.code = next_code
        used.add(next_code)
        pref.save(update_fields=["code"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_alter_colordefinition_created_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="usercolorpreference",
            name="code",
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.RunPython(
            drop_system_overrides_and_assign_codes,
            migrations.RunPython.noop,
        ),
        migrations.RemoveConstraint(
            model_name="usercolorpreference",
            name="uq_user_color_definition",
        ),
        migrations.RemoveField(
            model_name="usercolorpreference",
            name="color_definition",
        ),
        migrations.AlterField(
            model_name="usercolorpreference",
            name="code",
            field=models.PositiveSmallIntegerField(),
        ),
        migrations.AlterField(
            model_name="usercolorpreference",
            name="custom_hex",
            field=models.CharField(max_length=7),
        ),
        migrations.AddConstraint(
            model_name="usercolorpreference",
            constraint=models.UniqueConstraint(
                fields=("user", "code"),
                name="uq_user_color_code",
            ),
        ),
    ]
