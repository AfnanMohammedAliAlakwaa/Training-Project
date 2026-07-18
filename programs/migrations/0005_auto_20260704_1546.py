from django.db import migrations


DEFAULT_PROGRAMS = [
    "أمن سيبراني",
    "تقنية معلومات",
    "تقنية معلومات إنجليزي",
    "ذكاء اصطناعي",
    "نظم معلومات",
    "هندسة البرمجيات",

]


def create_default_programs(apps, schema_editor):
    Program = apps.get_model("programs", "Program")

    for program_name in DEFAULT_PROGRAMS:
        exists = Program.objects.filter(
            name=program_name
        ).exists()

        if not exists:
            Program.objects.create(
                name=program_name,
                specialization="",
                start_year=None,
            )


def remove_default_programs(apps, schema_editor):
    Program = apps.get_model("programs", "Program")

    Program.objects.filter(
        name__in=DEFAULT_PROGRAMS
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
    ("programs", "0004_remove_department_college_remove_program_department_and_more"),
]

    operations = [
        migrations.RunPython(
            create_default_programs,
            remove_default_programs
        ),
    ]