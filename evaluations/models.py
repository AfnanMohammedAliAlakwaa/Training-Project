from django.db import models
from programs.models import Program, AcademicYear


class EvaluationDomain(models.Model):
    name = models.CharField(max_length=200, verbose_name="اسم المعيار")
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="الوزن النسبي"
    )
    order = models.PositiveIntegerField(default=1, verbose_name="الترتيب")
    description = models.TextField(blank=True, null=True, verbose_name="الوصف")

    class Meta:
        verbose_name = "معيار تقييم"
        verbose_name_plural = "معايير التقييم"
        ordering = ["order"]

    def __str__(self):
        return f"{self.order}. {self.name} ({self.weight}%)"


class EvaluationIndicator(models.Model):
    domain = models.ForeignKey(
        EvaluationDomain,
        on_delete=models.CASCADE,
        related_name="indicators",
        verbose_name="المعيار"
    )
    text = models.TextField(verbose_name="نص المؤشر")
    order = models.PositiveIntegerField(default=1, verbose_name="الترتيب")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "مؤشر تقييم"
        verbose_name_plural = "مؤشرات التقييم"
        ordering = ["domain__order", "order"]

    def __str__(self):
        return self.text[:80]


class ProgramEvaluation(models.Model):
    STATUS_CHOICES = [
        ("draft", "مسودة"),
        ("in_progress", "قيد التقييم"),
        ("submitted", "مرسل للمراجعة"),
        ("approved", "معتمد"),
    ]

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="evaluations",
        verbose_name="البرنامج"
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name="evaluations",
        verbose_name="العام الأكاديمي"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        verbose_name="الحالة"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")

    class Meta:
        verbose_name = "تقييم برنامج"
        verbose_name_plural = "تقييمات البرامج"
        unique_together = ("program", "academic_year")

    def __str__(self):
        return f"{self.program.name} - {self.academic_year.name}"


class IndicatorScore(models.Model):
    SCORE_CHOICES = [
        (1, "غير مستوفي"),
        (2, "مستوفي جزئيًا"),
        (3, "مستوفي"),
        (4, "مستوفي بإتقان"),
        (5, "مستوفي بتميز"),
    ]

    evaluation = models.ForeignKey(
        ProgramEvaluation,
        on_delete=models.CASCADE,
        related_name="scores",
        verbose_name="التقييم"
    )
    indicator = models.ForeignKey(
        EvaluationIndicator,
        on_delete=models.CASCADE,
        related_name="scores",
        verbose_name="المؤشر"
    )
    score = models.PositiveSmallIntegerField(
        choices=SCORE_CHOICES,
        blank=True,
        null=True,
        verbose_name="درجة التوفر"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")

    class Meta:
        verbose_name = "درجة مؤشر"
        verbose_name_plural = "درجات المؤشرات"
        unique_together = ("evaluation", "indicator")

    def __str__(self):
        return f"{self.indicator} - {self.score}"