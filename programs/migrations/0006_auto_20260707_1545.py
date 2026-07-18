from django.db import migrations


NEW_PROGRAMS = [
    "علوم الحاسوب",
]


def add_new_default_programs(apps, schema_editor):
    Program = apps.get_model("programs", "Program")

    for program_name in NEW_PROGRAMS:
        Program.objects.get_or_create(
            name=program_name,
            defaults={
                "specialization": "",
                "start_year": None,
            }
        )


def remove_new_default_programs(apps, schema_editor):
    Program = apps.get_model("programs", "Program")

    Program.objects.filter(
        name__in=NEW_PROGRAMS
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0005_auto_20260704_1546"),
    ]

    operations = [
        migrations.RunPython(
            add_new_default_programs,
            remove_new_default_programs
        ),
    ]