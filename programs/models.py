from django.db import models
from django.utils import timezone


class College(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name="اسم الكلية",
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="الوصف",
    )

    class Meta:
        verbose_name = "كلية"
        verbose_name_plural = "الكليات"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(models.Model):
    college = models.ForeignKey(
        College,
        on_delete=models.CASCADE,
        related_name="departments",
        verbose_name="الكلية",
    )

    name = models.CharField(
        max_length=200,
        verbose_name="اسم القسم",
    )

    class Meta:
        verbose_name = "قسم"
        verbose_name_plural = "الأقسام"
        ordering = ["college__name", "name"]

    def __str__(self):
        return f"{self.name} - {self.college.name}"


class AcademicYear(models.Model):
    name = models.CharField(
        max_length=50,
        verbose_name="العام الأكاديمي",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط",
    )

    class Meta:
        verbose_name = "عام أكاديمي"
        verbose_name_plural = "الأعوام الأكاديمية"
        ordering = ["-name"]

    def __str__(self):
        return self.name


class Program(models.Model):
    PROGRAM_TYPE_CHOICES = [
        ("independent", "مستقل"),
        ("joint", "مشترك"),
        ("multiple", "متعدد"),
    ]

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        related_name="programs",
        blank=True,
        null=True,
        verbose_name="القسم",
    )

    name = models.CharField(
        max_length=200,
        verbose_name="اسم البرنامج",
    )

    specialization = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="التخصص",
    )

    start_year = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="سنة الإنشاء",
    )

    qualification_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="نوع المؤهل",
    )

    program_type = models.CharField(
        max_length=20,
        choices=PROGRAM_TYPE_CHOICES,
        default="independent",
        verbose_name="نوع البرنامج",
    )

    study_system = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="نظام الدراسة",
    )

    duration = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="مدة البرنامج",
    )

    program_manager = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="مسؤول البرنامج",
    )

    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="البريد الإلكتروني",
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="الهاتف",
    )

    website = models.URLField(
        blank=True,
        null=True,
        verbose_name="الموقع الإلكتروني",
    )

    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="العنوان",
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        verbose_name="تاريخ الإنشاء",
    )

    class Meta:
        verbose_name = "برنامج أكاديمي"
        verbose_name_plural = "البرامج الأكاديمية"
        ordering = ["name", "specialization", "start_year"]

    def __str__(self):
        if self.specialization:
            return f"{self.name} - {self.specialization}"

        return self.name
