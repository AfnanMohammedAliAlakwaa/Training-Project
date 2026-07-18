from django.core.management.base import BaseCommand
from django.db.models import Q

from dashboard.models import AcademicProgram, QualityStandard


PROGRAMS = [
    {
        "display_name": "هندسة البرمجيات",
        "dashboard_name": "هندسة البرمجيات",
        "specialization": "",
        "department": "قسم هندسة البرمجيات",
        "start_year": 2007,
    },
    {
        "display_name": "نظم معلومات - أعمال إلكترونية",
        "dashboard_name": "نظم معلومات",
        "specialization": "أعمال إلكترونية",
        "department": "قسم نظم المعلومات",
        "start_year": 2008,
    },
    {
        "display_name": "تقنية معلومات",
        "dashboard_name": "تقنية معلومات",
        "specialization": "",
        "department": "قسم تقنية المعلومات",
        "start_year": 2011,
    },
    {
        "display_name": "تقنية معلومات إنجليزي",
        "dashboard_name": "تقنية معلومات إنجليزي",
        "specialization": "",
        "department": "قسم تقنية المعلومات",
        "start_year": 2019,
    },
    {
        "display_name": "أمن سيبراني",
        "dashboard_name": "أمن سيبراني",
        "specialization": "",
        "department": "قسم الأمن السيبراني",
        "start_year": 2021,
    },
    {
        "display_name": "نظم معلومات - ذكاء أعمال",
        "dashboard_name": "نظم معلومات",
        "specialization": "ذكاء أعمال",
        "department": "قسم نظم المعلومات",
        "start_year": 2021,
    },
    {
        "display_name": "ذكاء اصطناعي",
        "dashboard_name": "ذكاء اصطناعي",
        "specialization": "",
        "department": "قسم الذكاء الاصطناعي",
        "start_year": 2024,
    },
]


STANDARDS = [
    {
        "number": 1,
        "title": "معلومات البرنامج",
        "weight": 5,
    },
    {
        "number": 2,
        "title": "رسالة وأهداف وخطط البرنامج",
        "weight": 10,
    },
    {
        "number": 3,
        "title": "مخرجات التعلم",
        "weight": 15,
    },
    {
        "number": 4,
        "title": "مواصفات البرنامج الأكاديمي",
        "weight": 20,
    },
    {
        "number": 5,
        "title": "الطلبة",
        "weight": 10,
    },
    {
        "number": 6,
        "title": "البنية المادية",
        "weight": 10,
    },
    {
        "number": 7,
        "title": "المكتبة",
        "weight": 10,
    },
    {
        "number": 8,
        "title": "إدارة العملية التعليمية",
        "weight": 20,
    },
]


# يبدأ من 2007-2008 وينتهي عند 2025-2026.
# لا تتم إضافة العام 2026-2027.
ACADEMIC_YEARS = [
    f"{year}-{year + 1}"
    for year in range(2007, 2026)
]

COLLEGE_NAME = "كلية الحاسبات وتكنولوجيا المعلومات"


class Command(BaseCommand):
    help = (
        "إضافة أو تحديث البيانات الأساسية: برامج dashboard، "
        "معايير الجودة، الكلية، الأقسام، البرامج، والأعوام الأكاديمية"
    )

    def _update_or_create_single(self, model, lookup, defaults):
        """
        تحديث أول سجل مطابق أو إنشاء سجل جديد عند عدم وجوده.

        لا تحذف هذه الدالة أي سجل قديم، وتمنع إنشاء سجل جديد
        في كل مرة يتم فيها تشغيل الأمر.
        """
        obj = model.objects.filter(**lookup).first()
        created = obj is None

        if created:
            obj = model.objects.create(
                **lookup,
                **defaults,
            )
        else:
            changed_fields = []

            for field, value in defaults.items():
                if getattr(obj, field, None) != value:
                    setattr(obj, field, value)
                    changed_fields.append(field)

            if changed_fields:
                obj.save(update_fields=changed_fields)

        return obj, created

    def _update_dashboard_program(self, program):
        """
        معالجة التخصص الفارغ سواء كان محفوظًا كقيمة فارغة أو NULL،
        حتى لا يتم إنشاء برنامج مكرر.
        """
        queryset = AcademicProgram.objects.filter(
            name=program["dashboard_name"],
        )

        specialization = program["specialization"]

        if specialization:
            queryset = queryset.filter(
                specialization=specialization,
            )
        else:
            queryset = queryset.filter(
                Q(specialization="")
                | Q(specialization__isnull=True)
            )

        obj = queryset.first()
        created = obj is None

        if created:
            obj = AcademicProgram.objects.create(
                name=program["dashboard_name"],
                specialization=specialization,
                start_year=program["start_year"],
                is_active=True,
            )
        else:
            obj.specialization = specialization
            obj.start_year = program["start_year"]
            obj.is_active = True

            obj.save(
                update_fields=[
                    "specialization",
                    "start_year",
                    "is_active",
                ]
            )

        return obj, created

    def handle(self, *args, **kwargs):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "بدء تحديث البيانات الأساسية..."
            )
        )

        # =====================================================
        # برامج ملفات التقييم في تطبيق dashboard
        # =====================================================
        for program in PROGRAMS:
            obj, created = self._update_dashboard_program(program)

            action = "تمت إضافة" if created else "تم تحديث"

            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} برنامج ملفات التقييم: {obj}"
                )
            )

        # =====================================================
        # معايير الجودة
        # =====================================================
        for standard in STANDARDS:
            obj, created = self._update_or_create_single(
                QualityStandard,
                {
                    "number": standard["number"],
                },
                {
                    "title": standard["title"],
                    "weight": standard["weight"],
                    "is_active": True,
                },
            )

            action = "تمت إضافة" if created else "تم تحديث"

            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} معيار الجودة: {obj}"
                )
            )

        # =====================================================
        # كتالوج البرامج في تطبيق programs
        # =====================================================
        try:
            from programs.models import (
                AcademicYear,
                College,
                Department,
                Program,
            )
        except (ImportError, LookupError) as error:
            self.stdout.write(
                self.style.WARNING(
                    "تعذر تحميل نماذج تطبيق programs، "
                    f"لذلك تم تجاوز تحديث الكتالوج: {error}"
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "تم تحديث بيانات dashboard الأساسية بنجاح."
                )
            )
            return

        # الكلية
        college, created = self._update_or_create_single(
            College,
            {
                "name": COLLEGE_NAME,
            },
            {
                "description": "",
            },
        )

        action = "تمت إضافة" if created else "تم تحديث"

        self.stdout.write(
            self.style.SUCCESS(
                f"{action} الكلية: {college.name}"
            )
        )

        # الأقسام
        departments = {}

        for program in PROGRAMS:
            department_name = program["department"]

            if department_name in departments:
                continue

            department, created = self._update_or_create_single(
                Department,
                {
                    "college": college,
                    "name": department_name,
                },
                {},
            )

            departments[department_name] = department
            action = "تمت إضافة" if created else "تم تحديث"

            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} القسم: {department.name}"
                )
            )

        # برامج الكتالوج
        for program in PROGRAMS:
            department = departments[program["department"]]

            # البحث بالاسم أولًا لتفادي إنشاء نسخة أخرى إذا كان البرنامج
            # موجودًا سابقًا بدون قسم أو بقسم مختلف.
            catalog_program = Program.objects.filter(
                name=program["display_name"],
            ).first()

            created = catalog_program is None

            defaults = {
                "department": department,
                "start_year": program["start_year"],
                "qualification_type": "بكالوريوس",
                "program_type": "independent",
                "study_system": "انتظام",
            }

            if created:
                catalog_program = Program.objects.create(
                    name=program["display_name"],
                    **defaults,
                )
            else:
                changed_fields = []

                for field, value in defaults.items():
                    if getattr(catalog_program, field, None) != value:
                        setattr(catalog_program, field, value)
                        changed_fields.append(field)

                if changed_fields:
                    catalog_program.save(
                        update_fields=changed_fields
                    )

            action = "تمت إضافة" if created else "تم تحديث"

            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} برنامج الكتالوج: "
                    f"{catalog_program.name}"
                )
            )

        # الأعوام الأكاديمية
        for year_name in ACADEMIC_YEARS:
            academic_year, created = self._update_or_create_single(
                AcademicYear,
                {
                    "name": year_name,
                },
                {
                    "is_active": True,
                },
            )

            action = "تمت إضافة" if created else "تم تحديث"

            self.stdout.write(
                self.style.SUCCESS(
                    f"{action} العام الأكاديمي: "
                    f"{academic_year.name}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "تم تحديث البيانات الأساسية بنجاح "
                "دون حذف أي بيانات موجودة."
            )
        )
