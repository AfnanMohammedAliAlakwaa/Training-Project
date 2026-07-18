from django.db import models
from django.utils import timezone

from dashboard.models import EvaluationFile
from evaluations.models import StandardEvaluationReview


class ImprovementPlan(models.Model):
    PRIORITY_CHOICES = [
        ("high", "عالية"),
        ("medium", "متوسطة"),
        ("low", "منخفضة"),
    ]

    STATUS_CHOICES = [
        ("proposed", "مقترحة"),
        ("in_progress", "قيد التنفيذ"),
        ("completed", "مكتملة"),
        ("closed", "مغلقة"),
    ]

    evaluation_file = models.ForeignKey(
        EvaluationFile,
        on_delete=models.CASCADE,
        related_name="improvement_plans",
        verbose_name="ملف التقييم",
    )

    standard_review = models.ForeignKey(
        StandardEvaluationReview,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="improvement_plans",
        verbose_name="المعيار المرتبط",
    )

    standard_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="رقم المعيار",
    )

    standard_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="عنوان المعيار",
    )

    title = models.CharField(
        max_length=255,
        verbose_name="عنوان خطة التحسين",
    )

    gap_description = models.TextField(
        blank=True,
        verbose_name="وصف الفجوة",
    )

    improvement_action = models.TextField(
        verbose_name="الإجراء التحسيني",
    )

    responsible_party = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="الجهة المسؤولة",
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="medium",
        verbose_name="الأولوية",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="proposed",
        verbose_name="حالة الخطة",
    )

    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ البداية",
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ الانتهاء المتوقع",
    )

    success_indicator = models.TextField(
        blank=True,
        verbose_name="مؤشر الإنجاز",
    )

    required_evidence = models.TextField(
        blank=True,
        verbose_name="الدليل المطلوب",
    )

    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخر تحديث",
    )

    class Meta:
        verbose_name = "خطة تحسين"
        verbose_name_plural = "خطط التحسين"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        if not self.due_date:
            return False

        if self.status in ["completed", "closed"]:
            return False

        return self.due_date < timezone.localdate()