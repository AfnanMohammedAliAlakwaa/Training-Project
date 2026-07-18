from django.conf import settings
from django.db import models
from django.utils import timezone


class AcademicProgram(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name="اسم البرنامج",
    )

    specialization = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="التخصص / المسار",
    )

    start_year = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="سنة بداية البرنامج",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "برنامج أكاديمي"
        verbose_name_plural = "البرامج الأكاديمية"
        ordering = ["name", "specialization"]

    def __str__(self):
        if self.specialization:
            return f"{self.name} - {self.specialization}"

        return self.name


class EvaluationFile(models.Model):
    program = models.ForeignKey(
        AcademicProgram,
        on_delete=models.CASCADE,
        related_name="evaluation_files",
        verbose_name="البرنامج",
    )

    academic_year = models.CharField(
        max_length=20,
        verbose_name="السنة الأكاديمية",
    )

    status = models.CharField(
        max_length=30,
        choices=[
            ("draft", "مسودة"),
            ("in_progress", "قيد الإدخال"),
            ("completed", "مكتمل"),
        ],
        default="draft",
        verbose_name="حالة الملف",
    )

    notes = models.TextField(
        blank=True,
        null=True,
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
        verbose_name = "ملف برنامج أكاديمي"
        verbose_name_plural = "ملفات البرامج الأكاديمية"

        # هذا النموذج يظهر له View فقط.
        default_permissions = ("view",)

        unique_together = (
            "program",
            "academic_year",
        )

        ordering = [
            "-academic_year",
            "program",
        ]

    def __str__(self):
        return f"{self.program} / {self.academic_year}"


class QualityStandard(models.Model):
    number = models.PositiveIntegerField(
        verbose_name="رقم المعيار",
    )

    title = models.CharField(
        max_length=250,
        verbose_name="عنوان المعيار",
    )

    weight = models.PositiveIntegerField(
        default=0,
        verbose_name="الوزن النسبي",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط",
    )

    class Meta:
        verbose_name = "معيار جودة"
        verbose_name_plural = "معايير الجودة"
        ordering = ["number"]

    def __str__(self):
        return f"{self.number}. {self.title}"


class StandardEntry(models.Model):
    evaluation_file = models.ForeignKey(
        EvaluationFile,
        on_delete=models.CASCADE,
        related_name="standard_entries",
        verbose_name="ملف التقييم",
    )

    standard = models.ForeignKey(
        QualityStandard,
        on_delete=models.CASCADE,
        related_name="entries",
        verbose_name="المعيار",
    )

    form_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="بيانات الحقول العامة",
    )

    completion_status = models.CharField(
        max_length=30,
        choices=[
            ("empty", "فارغ"),
            ("partial", "مكتمل جزئيًا"),
            ("complete", "مكتمل"),
        ],
        default="empty",
        verbose_name="حالة الاكتمال",
    )

    completion_percentage = models.PositiveIntegerField(
        default=0,
        verbose_name="نسبة الاكتمال",
    )

    saved_as_draft = models.BooleanField(
        default=True,
        verbose_name="محفوظ كمسودة",
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
        verbose_name = "بيانات معيار"
        verbose_name_plural = "بيانات المعايير"

        # هذا النموذج يظهر له View فقط.
        default_permissions = ("view",)

        unique_together = (
            "evaluation_file",
            "standard",
        )

        ordering = [
            "standard__number",
        ]

    def __str__(self):
        return f"{self.evaluation_file} - {self.standard}"


class EvidenceAttachment(models.Model):
    standard_entry = models.ForeignKey(
        StandardEntry,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="بيانات المعيار",
    )

    title = models.CharField(
        max_length=250,
        verbose_name="اسم المرفق",
    )

    file = models.FileField(
        upload_to="evidence_attachments/",
        verbose_name="الملف",
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الرفع",
    )

    class Meta:
        verbose_name = "مرفق شاهد"
        verbose_name_plural = "مرفقات الشواهد"

    def __str__(self):
        return self.title


class StudentLevelCount(models.Model):
    evaluation_file = models.ForeignKey(
        EvaluationFile,
        on_delete=models.CASCADE,
        related_name="student_level_counts",
        verbose_name="ملف التقييم",
    )

    level_name = models.CharField(
        max_length=100,
        verbose_name="المستوى",
    )

    male_count = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد الطلاب",
    )

    female_count = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد الطالبات",
    )

    class Meta:
        verbose_name = "عدد الطلبة حسب المستوى"
        verbose_name_plural = "أعداد الطلبة حسب المستويات"

    @property
    def total_count(self):
        return self.male_count + self.female_count

    def __str__(self):
        return f"{self.evaluation_file} - {self.level_name}"


class GraduateRecord(models.Model):
    male_count = models.PositiveIntegerField(
        default=0,
    )

    female_count = models.PositiveIntegerField(
        default=0,
    )

    evaluation_file = models.ForeignKey(
        EvaluationFile,
        on_delete=models.CASCADE,
        related_name="graduate_records",
        verbose_name="ملف التقييم",
    )

    academic_year = models.CharField(
        max_length=20,
        verbose_name="العام الجامعي",
    )

    graduates_count = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد الخريجين",
    )

    cumulative_gpa = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="المعدل التراكمي",
    )

    class Meta:
        verbose_name = "سجل خريجين"
        verbose_name_plural = "أعداد الخريجين"

    def __str__(self):
        return f"{self.evaluation_file} - {self.academic_year}"


class CourseRecord(models.Model):
    evaluation_file = models.ForeignKey(
        EvaluationFile,
        on_delete=models.CASCADE,
        related_name="course_records",
        verbose_name="ملف التقييم",
    )

    course_name = models.CharField(
        max_length=250,
        verbose_name="اسم المقرر",
    )

    course_code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="رمز المقرر",
    )

    credit_hours = models.PositiveIntegerField(
        default=0,
        verbose_name="الساعات",
    )

    level = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="المستوى",
    )

    requirement_type = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="نوع المتطلب",
    )

    has_specification = models.BooleanField(
        default=False,
        verbose_name="له توصيف",
    )

    class Meta:
        verbose_name = "مقرر دراسي"
        verbose_name_plural = "المقررات الدراسية"

    def __str__(self):
        return self.course_name


class FacultyMemberRecord(models.Model):
    evaluation_file = models.ForeignKey(
        EvaluationFile,
        on_delete=models.CASCADE,
        related_name="faculty_members",
        verbose_name="ملف التقييم",
    )

    name = models.CharField(
        max_length=250,
        verbose_name="الاسم",
    )

    qualification = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="المؤهل",
    )

    qualification_year = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="سنة الحصول عليه",
    )

    academic_rank = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="المرتبة الأكاديمية",
    )

    rank_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="تاريخ الحصول عليها",
    )

    employment_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="متفرغ / غير متفرغ",
    )

    teaching_load = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="النصاب التدريسي",
    )

    class Meta:
        verbose_name = "عضو هيئة تدريس"
        verbose_name_plural = "أعضاء هيئة التدريس"

    def __str__(self):
        return self.name


class InfrastructureRecord(models.Model):
    evaluation_file = models.ForeignKey(
        EvaluationFile,
        on_delete=models.CASCADE,
        related_name="infrastructure_records",
        verbose_name="ملف التقييم",
    )

    facility_type = models.CharField(
        max_length=200,
        verbose_name="نوع المرفق",
    )

    count = models.PositiveIntegerField(
        default=0,
        verbose_name="العدد",
    )

    area = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="المساحة",
    )

    equipment = models.TextField(
        blank=True,
        null=True,
        verbose_name="التجهيزات",
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="ملاحظات",
    )

    class Meta:
        verbose_name = "بنية مادية"
        verbose_name_plural = "البنية المادية"

    def __str__(self):
        return f"{self.evaluation_file} - {self.facility_type}"


class LibrarySourceRecord(models.Model):
    evaluation_file = models.ForeignKey(
        EvaluationFile,
        on_delete=models.CASCADE,
        related_name="library_sources",
        verbose_name="ملف التقييم",
    )

    source_type = models.CharField(
        max_length=150,
        verbose_name="نوع المصدر",
    )

    title = models.CharField(
        max_length=250,
        verbose_name="العنوان / الوصف",
    )

    count = models.PositiveIntegerField(
        default=0,
        verbose_name="العدد",
    )

    release_year = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="سنة الإصدار",
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="ملاحظات",
    )

    class Meta:
        verbose_name = "مصدر مكتبي"
        verbose_name_plural = "مصادر المكتبة"

    def __str__(self):
        return self.title


class EducationProcessRecord(models.Model):
    evaluation_file = models.ForeignKey(
        EvaluationFile,
        on_delete=models.CASCADE,
        related_name="education_process_records",
        verbose_name="ملف التقييم",
    )

    item = models.CharField(
        max_length=250,
        verbose_name="البند",
    )

    status = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="الحالة",
    )

    value = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="النسبة / العدد",
    )

    evidence = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        verbose_name="المرفق / الشاهد",
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="ملاحظات",
    )

    class Meta:
        verbose_name = "مؤشر عملية تعليمية"
        verbose_name_plural = "مؤشرات العملية التعليمية"

    def __str__(self):
        return f"{self.evaluation_file} - {self.item}"


class DataEntryTableRecord(models.Model):
    """
    هذا الموديل مخصص لحفظ الجداول الديناميكية الجديدة
    في صفحة إدخال البيانات.

    الفكرة:
    - أي جدول جديد في HTML يكون له id.
    - الحقول داخل الجدول يكون لها name.
    - JavaScript يجمع بيانات الجدول ويرسلها كـ JSON.
    - هذا الموديل يحفظ الصفوف كما هي بدون الحاجة
      لإضافة موديل جديد لكل جدول.
    """

    evaluation_file = models.ForeignKey(
        EvaluationFile,
        on_delete=models.CASCADE,
        related_name="dynamic_table_records",
        verbose_name="ملف التقييم",
    )

    standard_key = models.CharField(
        max_length=80,
        blank=True,
        default="",
        verbose_name="مفتاح المعيار",
    )

    table_key = models.CharField(
        max_length=120,
        verbose_name="معرف الجدول",
    )

    table_title = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="عنوان الجدول",
    )

    rows = models.JSONField(
        default=list,
        blank=True,
        verbose_name="صفوف الجدول",
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
        verbose_name = "سجل جدول إدخال بيانات"
        verbose_name_plural = "سجلات جداول إدخال البيانات"

        unique_together = (
            "evaluation_file",
            "table_key",
        )

        ordering = [
            "standard_key",
            "table_key",
        ]

        indexes = [
            models.Index(
                fields=[
                    "evaluation_file",
                    "table_key",
                ],
            ),
            models.Index(
                fields=[
                    "standard_key",
                ],
            ),
        ]

    def __str__(self):
        if self.table_title:
            return (
                f"{self.evaluation_file} - "
                f"{self.table_title}"
            )

        return (
            f"{self.evaluation_file} - "
            f"{self.table_key}"
        )


class ReportExportLog(models.Model):
    """
    سجل آخر التقارير التي تم تصديرها فعليًا
    من واجهة التقارير.

    هذا الجدول لا يحفظ الملف نفسه؛
    يحفظ بيانات عملية التصدير للمتابعة والتدقيق.
    """

    EXPORT_FORMAT_CHOICES = [
        ("PDF", "PDF"),
        ("EXCEL", "Excel"),
    ]

    report_type = models.CharField(
        max_length=80,
        blank=True,
        default="all",
        verbose_name="معرف نوع التقرير",
    )

    report_title = models.CharField(
        max_length=255,
        verbose_name="نوع التقرير",
    )

    program_name = models.CharField(
        max_length=255,
        blank=True,
        default="اختار البرنامج",
        verbose_name="البرنامج",
    )

    college_name = models.CharField(
        max_length=255,
        blank=True,
        default="جميع الكليات",
        verbose_name="الكلية",
    )

    academic_year = models.CharField(
        max_length=30,
        blank=True,
        default="جميع السنوات",
        verbose_name="السنة الأكاديمية",
    )

    export_format = models.CharField(
        max_length=20,
        choices=EXPORT_FORMAT_CHOICES,
        verbose_name="صيغة التصدير",
    )

    exported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dashboard_report_exports",
        verbose_name="تم التصدير بواسطة",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ التصدير",
    )

    class Meta:
        verbose_name = "سجل تصدير تقرير"
        verbose_name_plural = "سجل تصدير التقارير"

        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "-created_at",
                ],
            ),
            models.Index(
                fields=[
                    "report_type",
                    "export_format",
                ],
            ),
            models.Index(
                fields=[
                    "program_name",
                    "academic_year",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.report_title} - "
            f"{self.program_name} - "
            f"{self.academic_year} - "
            f"{self.export_format}"
        )


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ("login", "تسجيل دخول"),
        ("create", "إضافة"),
        ("update", "تعديل"),
        ("delete", "حذف"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="المستخدم",
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name="نوع العملية",
    )

    section = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="القسم",
    )

    standard_label = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="المعيار",
    )

    model_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="نوع البيانات",
    )

    object_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="رقم السجل",
    )

    object_repr = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="البرنامج",
    )

    changes = models.TextField(
        blank=True,
        verbose_name="تفاصيل التغيير",
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="عنوان IP",
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name="الجهاز / المتصفح",
    )

    url = models.TextField(
        blank=True,
        verbose_name="الرابط",
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="وقت العملية",
    )

    class Meta:
        verbose_name = "سجل نشاط"
        verbose_name_plural = "سجل نشاط النظام"

        # سجل النشاط للعرض فقط.
        default_permissions = ("view",)

        ordering = [
            "-created_at",
        ]

    def __str__(self):
        username = (
            self.user.username
            if self.user
            else "مستخدم غير معروف"
        )

        return (
            f"{username} - "
            f"{self.get_action_display()}"
        )


class UserActivityLog(ActivityLog):
    """
    نموذج وسيط لعرض سجل النشاط
    تحت قسم المصادقة في لوحة الإدارة،
    بدون إنشاء جدول جديد في قاعدة البيانات.
    """

    class Meta:
        proxy = True
        app_label = "auth"

        verbose_name = "سجل نشاط النظام"
        verbose_name_plural = "سجل نشاط النظام"

        # نموذج سجل النشاط الوسيط للعرض فقط.
        default_permissions = ("view",)


def log_activity(
    request,
    action,
    section,
    object_repr="",
    model_name="",
    object_id="",
    changes="",
    standard_label="",
):
    """
    حفظ نشاط المستخدم الحالي مع معلومات الطلب والجهاز.

    تعيد سجل النشاط بعد إنشائه،
    أو None إذا لم يكن المستخدم مسجل الدخول.
    """

    user = getattr(
        request,
        "user",
        None,
    )

    if not user or not user.is_authenticated:
        return None

    forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR",
        "",
    )

    ip_address = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else request.META.get("REMOTE_ADDR")
    )

    return ActivityLog.objects.create(
        user=user,
        action=action,
        section=section,
        standard_label=standard_label,
        model_name=model_name,
        object_id=str(object_id or ""),
        object_repr=str(object_repr or "")[:255],
        changes=str(changes or ""),
        ip_address=ip_address,
        user_agent=request.META.get(
            "HTTP_USER_AGENT",
            "",
        )[:1000],
        url=request.get_full_path(),
    )