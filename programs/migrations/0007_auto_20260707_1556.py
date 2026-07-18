from django.db import migrations


def remove_computer_science(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.filter(name="علوم الحاسوب").delete()


def restore_computer_science(apps, schema_editor):
    Program = apps.get_model("programs", "Program")
    Program.objects.get_or_create(
        name="علوم الحاسوب",
        defaults={
            "specialization": "",
            "start_year": None,
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ("programs", "0006_auto_20260707_1545"),
    ]

    operations = [
        migrations.RunPython(
            remove_computer_science,
            restore_computer_science
        ),
    ]