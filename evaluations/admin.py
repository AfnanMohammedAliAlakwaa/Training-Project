from decimal import Decimal, InvalidOperation

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ProgramEvaluationReview,
    StandardEvaluationReview,
)


# تسمية القسم في القائمة الجانبية
ProgramEvaluationReview._meta.verbose_name = "تقييم برنامج"
ProgramEvaluationReview._meta.verbose_name_plural = "تقييمات البرامج"


# ==========================================================
# أدوات عرض الأرقام
# ==========================================================

def _decimal_text(value):
    """
    تحويل الرقم إلى منزلتين عشريتين باستخدام النقطة
    بدل الفاصلة المحلية التي يعرضها Django.
    """
    if value is None or value == "":
        return "—"

    try:
        number = Decimal(str(value))
        return f"{number:.2f}"
    except (InvalidOperation, ValueError, TypeError):
        return str(value)


def _number_html(value, suffix=""):
    if value is None or value == "":
        return "—"

    return format_html(
        '<span class="aq-admin-number" dir="ltr">{}{}</span>',
        _decimal_text(value),
        suffix,
    )


def _percentage_html(value):
    return _number_html(value, "%")


# ==========================================================
# تفاصيل معايير التقييم داخل تقييم البرنامج
# ==========================================================

class StandardEvaluationReviewInline(admin.TabularInline):
    model = StandardEvaluationReview

    extra = 0
    can_delete = False
    show_change_link = False

    verbose_name = "تفصيل معيار"
    verbose_name_plural = "تفاصيل تقييم المعايير"

    fields = (
        "standard_display",
        "weight_display",
        "auto_score_display",
        "reviewer_score_display",
        "auto_percentage_display",
        "reviewer_percentage_display",
        "auto_weighted_score_display",
        "reviewer_weighted_score_display",
    )

    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "standard",
        )

    @admin.display(description="المعيار")
    def standard_display(self, obj):
        return obj.standard

    @admin.display(description="وزن المعيار")
    def weight_display(self, obj):
        return _percentage_html(obj.weight)

    @admin.display(description="درجة النظام")
    def auto_score_display(self, obj):
        if obj.auto_score is None:
            return "—"

        return obj.get_auto_score_display()

    @admin.display(description="درجة المراجع")
    def reviewer_score_display(self, obj):
        if obj.reviewer_score is None:
            return "—"

        return obj.get_reviewer_score_display()

    @admin.display(description="نسبة النظام")
    def auto_percentage_display(self, obj):
        return _percentage_html(obj.auto_percentage)

    @admin.display(description="نسبة المراجع")
    def reviewer_percentage_display(self, obj):
        return _percentage_html(obj.reviewer_percentage)

    @admin.display(description="المساهمة الآلية")
    def auto_weighted_score_display(self, obj):
        return _number_html(obj.auto_weighted_score)

    @admin.display(description="مساهمة المراجع")
    def reviewer_weighted_score_display(self, obj):
        return _number_html(obj.reviewer_weighted_score)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True


# ==========================================================
# تقييمات البرامج المستخدمة في واجهة النظام
# ==========================================================

@admin.register(ProgramEvaluationReview)
class ProgramEvaluationReviewAdmin(admin.ModelAdmin):
    actions = None
    list_filter = ()
    list_per_page = 24
    empty_value_display = "—"

    list_display = (
        "program_display",
        "academic_year_display",
        "standards_status_display",
        "auto_percentage_list",
        "reviewer_percentage_list",
        "final_percentage_list",
        "final_rating_display",
    )

    list_display_links = (
        "program_display",
    )

    search_fields = (
        "evaluation_file__program__name",
        "evaluation_file__program__specialization",
        "evaluation_file__academic_year",
    )

    ordering = (
        "-updated_at",
    )

    readonly_fields = (
        "evaluation_file_display",
        "status_display",
        "overall_auto_percentage_display",
        "overall_reviewer_percentage_display",
        "final_percentage_display",
        "final_rating_display",
        "general_notes_display",
    )

    fieldsets = (
        (
            "بيانات التقييم",
            {
                "fields": (
                    "evaluation_file_display",
                    "status_display",
                ),
            },
        ),
        (
            "نتائج التقييم",
            {
                "fields": (
                    "overall_auto_percentage_display",
                    "overall_reviewer_percentage_display",
                    "final_percentage_display",
                    "final_rating_display",
                ),
            },
        ),
        (
            "الملاحظات العامة",
            {
                "fields": (
                    "general_notes_display",
                ),
            },
        ),
    )

    inlines = ()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "evaluation_file",
                "evaluation_file__program",
            )
            .prefetch_related(
                "standard_reviews",
            )
        )

    # ======================================================
    # أدوات حساب الحالة الفعلية للمعايير
    # ======================================================

    def _standard_status_counts(self, obj):
        """
        إرجاع أعداد المعايير حسب حالتها الفعلية.

        الحالة العامة للبرنامج لا تعتمد هنا على الحقل status فقط،
        بل على حالات جميع StandardEvaluationReview المرتبطة به.
        """
        if not obj:
            return {
                "total": 0,
                "reviewed": 0,
                "draft": 0,
                "empty": 0,
                "other": 0,
            }

        standard_reviews = list(obj.standard_reviews.all())

        total_count = len(standard_reviews)
        reviewed_count = 0
        draft_count = 0
        empty_count = 0
        other_count = 0

        for standard_review in standard_reviews:
            status = standard_review.review_status

            if status == "reviewed":
                reviewed_count += 1
            elif status == "draft":
                draft_count += 1
            elif status == "empty":
                empty_count += 1
            else:
                other_count += 1

        return {
            "total": total_count,
            "reviewed": reviewed_count,
            "draft": draft_count,
            "empty": empty_count,
            "other": other_count,
        }

    @admin.display(description="حالة المعايير")
    def standards_status_display(self, obj):
        """
        عرض الحالة الحقيقية للتقييم:

        - معتمد بالكامل: جميع المعايير معتمدة.
        - قيد المراجعة: يوجد اعتماد أو مسودة جزئية.
        - غير مراجع: لا يوجد أي معيار معتمد أو محفوظ كمسودة.
        """
        counts = self._standard_status_counts(obj)

        total_count = counts["total"]
        reviewed_count = counts["reviewed"]
        draft_count = counts["draft"]
        empty_count = counts["empty"]
        other_count = counts["other"]

        if total_count == 0:
            return format_html(
                '<span style="font-weight:800;color:#64748b;">لا توجد معايير</span>'
            )

        if reviewed_count == total_count:
            return format_html(
                '<span style="font-weight:900;color:#16865c;">'
                'معتمد بالكامل ({}/{})'
                '</span>',
                reviewed_count,
                total_count,
            )

        not_saved_count = empty_count + other_count

        if reviewed_count > 0 or draft_count > 0:
            return format_html(
                '<span style="font-weight:900;color:#9a6b00;">قيد المراجعة</span>'
                '<br>'
                '<small style="color:#475569;">'
                'معتمد: {} / مسودة: {} / غير محفوظ: {}'
                '</small>',
                reviewed_count,
                draft_count,
                not_saved_count,
            )

        return format_html(
            '<span style="font-weight:900;color:#64748b;">غير مراجع</span>'
            '<br>'
            '<small style="color:#64748b;">غير محفوظ: {}/{}</small>',
            not_saved_count,
            total_count,
        )

    # ======================================================
    # بيانات صفحة القائمة
    # ======================================================

    @admin.display(
        description="البرنامج",
        ordering="evaluation_file__program__name",
    )
    def program_display(self, obj):
        program = obj.evaluation_file.program
        specialization = getattr(
            program,
            "specialization",
            None,
        )

        if specialization:
            return f"{program.name} - {specialization}"

        return program.name

    @admin.display(
        description="السنة الأكاديمية",
        ordering="evaluation_file__academic_year",
    )
    def academic_year_display(self, obj):
        return obj.evaluation_file.academic_year

    @admin.display(description="الحالة")
    def status_display(self, obj):
        """
        نفس الحالة التفصيلية المعروضة في القائمة،
        بدل عرض قيمة status العامة المضللة.
        """
        return self.standards_status_display(obj)

    @admin.display(
        description="النسبة الآلية",
        ordering="overall_auto_percentage",
    )
    def auto_percentage_list(self, obj):
        return _percentage_html(
            obj.overall_auto_percentage
        )

    @admin.display(
        description="نسبة المراجع",
        ordering="overall_reviewer_percentage",
    )
    def reviewer_percentage_list(self, obj):
        return _percentage_html(
            obj.overall_reviewer_percentage
        )

    @admin.display(
        description="النسبة النهائية",
        ordering="final_percentage",
    )
    def final_percentage_list(self, obj):
        return _percentage_html(
            obj.final_percentage
        )

    # ======================================================
    # بيانات صفحة عرض التقييم
    # ======================================================

    @admin.display(description="ملف بيانات البرنامج")
    def evaluation_file_display(self, obj):
        if not obj:
            return "—"

        return obj.evaluation_file

    @admin.display(description="النسبة الآلية")
    def overall_auto_percentage_display(self, obj):
        if not obj:
            return "—"

        return _percentage_html(
            obj.overall_auto_percentage
        )

    @admin.display(description="نسبة المراجع")
    def overall_reviewer_percentage_display(self, obj):
        if not obj:
            return "—"

        return _percentage_html(
            obj.overall_reviewer_percentage
        )

    @admin.display(description="النسبة النهائية")
    def final_percentage_display(self, obj):
        if not obj:
            return "—"

        return _percentage_html(
            obj.final_percentage
        )

    @admin.display(
        description="التقدير النهائي",
        ordering="final_status_label",
    )
    def final_rating_display(self, obj):
        if not obj:
            return "—"

        return obj.final_status_label or "غير محدد"

    @admin.display(description="ملاحظات عامة")
    def general_notes_display(self, obj):
        if not obj:
            return "—"

        return obj.general_notes or "لا توجد ملاحظات عامة."

    def change_view(
        self,
        request,
        object_id,
        form_url="",
        extra_context=None,
    ):
        extra_context = extra_context or {}
        extra_context["title"] = "عرض تقييم برنامج"

        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context,
        )

    # التقييم ينشأ ويعدل من واجهة النظام
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True
