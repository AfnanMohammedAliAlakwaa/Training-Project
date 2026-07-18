from django.db import models
from django.conf import settings

from programs.models import Program, AcademicYear


# ============================================================
# التقييم القديم الموجود عندك
# نتركه كما هو حتى لا تنكسر الجداول القديمة
# ============================================================

class EvaluationDomain(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name="اسم المعيار"
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="الوزن النسبي"
    )

    order = models.PositiveIntegerField(
        default=1,
        verbose_name="الترتيب"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="الوصف"
    )

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

    text = models.TextField(
        verbose_name="نص المؤشر"
    )

    order = models.PositiveIntegerField(
        default=1,
        verbose_name="الترتيب"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط"
    )

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

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخر تحديث"
    )

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

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="ملاحظات"
    )

    class Meta:
        verbose_name = "درجة مؤشر"
        verbose_name_plural = "درجات المؤشرات"
        unique_together = ("evaluation", "indicator")

    def __str__(self):
        return f"{self.indicator} - {self.score}"


# ============================================================
# التقييم الجديد المرتبط بصفحة إدخال البيانات
# ProgramEvaluationReview = الحاوية العامة للتخصص/ملف البيانات
# StandardEvaluationReview = المسودة/الاعتماد لكل معيار مستقل
# ============================================================

class ProgramEvaluationReview(models.Model):
    STATUS_CHOICES = [
        ("draft", "مسودة"),
        ("reviewed", "معتمد"),
    ]

    evaluation_file = models.OneToOneField(
        "dashboard.EvaluationFile",
        on_delete=models.CASCADE,
        related_name="quality_review",
        verbose_name="ملف بيانات البرنامج",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        verbose_name="حالة التقييم العامة",
    )

    overall_auto_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="النسبة الآلية",
    )

    overall_reviewer_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="نسبة المراجع",
    )

    final_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="النسبة النهائية",
    )

    final_status_label = models.CharField(
        max_length=100,
        default="غير مستوفي",
        verbose_name="التقدير النهائي",
    )

    general_notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات عامة",
    )

    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="generated_program_quality_reviews",
        verbose_name="تم التوليد بواسطة",
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_program_quality_reviews",
        verbose_name="تم الاعتماد العام بواسطة",
    )

    generated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاريخ التوليد / التحديث",
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
        verbose_name = "تقييم جودة البرنامج"
        verbose_name_plural = "تقييمات جودة البرامج"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"تقييم الجودة - {self.evaluation_file}"


class StandardEvaluationReview(models.Model):
    SCORE_CHOICES = [
        (1, "غير مستوفي"),
        (2, "مستوفي جزئيًا"),
        (3, "مستوفي"),
        (4, "مستوفي بإتقان"),
        (5, "مستوفي بتميز"),
    ]

    REVIEW_STATUS_CHOICES = [
        ("empty", "غير محفوظ"),
        ("draft", "مسودة"),
        ("reviewed", "معتمد"),
    ]

    review = models.ForeignKey(
        ProgramEvaluationReview,
        on_delete=models.CASCADE,
        related_name="standard_reviews",
        verbose_name="تقييم البرنامج",
    )

    standard = models.ForeignKey(
        "dashboard.QualityStandard",
        on_delete=models.CASCADE,
        related_name="quality_standard_reviews",
        verbose_name="المعيار",
    )

    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default="empty",
        verbose_name="حالة مراجعة المعيار",
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="وزن المعيار",
    )

    auto_score = models.PositiveSmallIntegerField(
        choices=SCORE_CHOICES,
        default=1,
        verbose_name="درجة النظام",
    )

    reviewer_score = models.PositiveSmallIntegerField(
        choices=SCORE_CHOICES,
        null=True,
        blank=True,
        verbose_name="درجة المراجع",
    )

    auto_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="نسبة النظام",
    )

    reviewer_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="نسبة المراجع",
    )

    auto_weighted_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        verbose_name="الدرجة الوزنية الآلية",
    )

    reviewer_weighted_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="الدرجة الوزنية للمراجع",
    )

    auto_notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات النظام",
    )

    reviewer_notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات المراجع",
    )

    strengths = models.TextField(
        blank=True,
        verbose_name="نقاط القوة",
    )

    weaknesses = models.TextField(
        blank=True,
        verbose_name="نقاط الضعف",
    )

    improvement_plan = models.TextField(
        blank=True,
        verbose_name="خطة التحسين",
    )

    execution_time = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="زمن التنفيذ",
    )

    modified_by_reviewer = models.BooleanField(
        default=False,
        verbose_name="تم تعديل تقييم النظام",
    )

    saved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="saved_quality_standard_drafts",
        verbose_name="تم الحفظ بواسطة",
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_quality_standards",
        verbose_name="تم اعتماد المعيار بواسطة",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاريخ اعتماد المعيار",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "تقييم معيار"
        verbose_name_plural = "تقييم المعايير"
        unique_together = ("review", "standard")
        ordering = ["standard__number"]

    def __str__(self):
        return f"{self.standard} - {self.review}"


class IndicatorEvaluationReview(models.Model):
    SCORE_CHOICES = StandardEvaluationReview.SCORE_CHOICES

    standard_review = models.ForeignKey(
        StandardEvaluationReview,
        on_delete=models.CASCADE,
        related_name="indicator_reviews",
        verbose_name="تقييم المعيار",
    )

    indicator_key = models.CharField(
        max_length=120,
        verbose_name="مفتاح المؤشر",
    )

    indicator_text = models.TextField(
        verbose_name="نص المؤشر",
    )

    auto_score = models.PositiveSmallIntegerField(
        choices=SCORE_CHOICES,
        default=1,
        verbose_name="درجة النظام",
    )

    reviewer_score = models.PositiveSmallIntegerField(
        choices=SCORE_CHOICES,
        null=True,
        blank=True,
        verbose_name="درجة المراجع",
    )

    auto_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="نسبة تحقق المؤشر",
    )

    auto_notes = models.TextField(
        blank=True,
        verbose_name="ملاحظة النظام",
    )

    reviewer_notes = models.TextField(
        blank=True,
        verbose_name="ملاحظة المراجع",
    )

    data_snapshot = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="تفاصيل الفحص الآلي",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "تقييم مؤشر"
        verbose_name_plural = "تقييم المؤشرات"
        unique_together = ("standard_review", "indicator_key")
        ordering = ["id"]

    def __str__(self):
        return self.indicator_text[:80]
