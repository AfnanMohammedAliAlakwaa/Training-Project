from django.core.management.base import BaseCommand
from dashboard.models import AcademicProgram, QualityStandard


class Command(BaseCommand):
    help = "إضافة البرامج الأكاديمية ومعايير الجودة الأساسية"

    def handle(self, *args, **kwargs):
        programs = [
            {
                "name": "تقنية معلومات",
                "specialization": "",
                "start_year": 2011,
            },
            {
                "name": "تقنية معلومات انجليزي",
                "specialization": "",
                "start_year": 2019,
            },
            {
                "name": "نظم معلومات",
                "specialization": "ذكاء أعمال",
                "start_year": 2021,
            },
            {
                "name": "نظم معلومات",
                "specialization": "أعمال إلكترونية",
                "start_year": 2021,
            },
            {
                "name": "أمن سيبراني",
                "specialization": "",
                "start_year": 2021,
            },
            {
                "name": "هندسة البرمجيات",
                "specialization": "",
                "start_year": 2007,
            },
            {
                "name": "ذكاء اصطناعي",
                "specialization": "",
                "start_year": 2024,
            },
        ]

        standards = [
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
                "title": "مواصفات البرنامج",
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

        for program in programs:
            obj, created = AcademicProgram.objects.update_or_create(
                name=program["name"],
                specialization=program["specialization"],
                defaults={
                    "start_year": program["start_year"],
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"تمت إضافة البرنامج: {obj}"))
            else:
                self.stdout.write(self.style.WARNING(f"تم تحديث البرنامج: {obj}"))

        for standard in standards:
            obj, created = QualityStandard.objects.update_or_create(
                number=standard["number"],
                defaults={
                    "title": standard["title"],
                    "weight": standard["weight"],
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"تمت إضافة المعيار: {obj}"))
            else:
                self.stdout.write(self.style.WARNING(f"تم تحديث المعيار: {obj}"))

        self.stdout.write(self.style.SUCCESS("تمت تعبئة البيانات الأساسية بنجاح."))