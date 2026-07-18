import json
import re
from django import forms
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group, User
from django.db.models import CharField, Count, F, OuterRef, Q, Subquery, Value
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Cast, Coalesce, Lower, Replace
from django.urls import reverse
from evaluations.models import StandardEvaluationReview
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from .models import (
    EvaluationFile,
    QualityStandard,
    StandardEntry,
    UserActivityLog,
)
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

admin.site.site_header = "إدارة نظام الجودة الأكاديمية"
admin.site.site_title = "إدارة النظام"
admin.site.index_title = "لوحة إدارة النظام"

from django.contrib import admin


class ViewOnlyAdminMixin:
    """
    يجعل النموذج ظاهرًا للقراءة فقط داخل لوحة الإدارة.
    يمنع الإضافة والتعديل والحذف حتى للمستخدم صاحب الصلاحيات.
    """

    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        opts = self.model._meta

        return (
            request.user.is_superuser
            or request.user.has_perm(
                f"{opts.app_label}.view_{opts.model_name}"
            )
        )
# ==========================================================
# حالات الملفات والمعايير كنص ملوّن فقط بدون مربعات
# ==========================================================

def render_status_text(value):
    if not value:
        return mark_safe(
            '<span class="aq-status-text aq-status-muted">غير محدد</span>'
        )

    raw = str(value).strip().lower()

    completed_values = [
        "completed",
        "complete",
        "done",
        "مكتمل",
        "نهائي",
    ]

    draft_values = [
        "draft",
        "مسودة",
        "مسوده",
    ]

    progress_values = [
        "in_progress",
        "in progress",
        "progress",
        "قيد الإدخال",
        "قيد الادخال",
        "قيد إدخال",
        "قيد ادخال",
        "partial",
        "partially_completed",
        "مكتمل جزئياً",
        "مكتمل جزئيا",
        "جزئي",
    ]

    empty_values = [
        "empty",
        "فارغ",
        "غير مكتمل",
        "not_started",
        "not started",
    ]

    if raw in completed_values:
        label = "مكتمل"
        css_class = "aq-status-success"
    elif raw in draft_values:
        label = "مسودة"
        css_class = "aq-status-draft"
    elif raw in progress_values:
        label = "قيد الإدخال"
        css_class = "aq-status-progress"
    elif raw in empty_values:
        label = "غير مكتمل"
        css_class = "aq-status-muted"
    else:
        label = str(value)
        css_class = "aq-status-muted"

    return format_html(
        '<span class="aq-status-text {}">{}</span>',
        css_class,
        label,
    )


# ==========================================================
# تنسيق بيانات form_data بدل ظهورها كـ JSON خام
# ==========================================================

FIELD_LABELS = {
    "notes": "ملاحظات",
    "general_notes": "ملاحظات عامة",
    "library_notes": "ملاحظات المكتبة",
    "library_automation": "أتمتة المكتبة",
    "library_has_automation": "هل توجد أتمتة؟",
    "library_total_area": "المساحة الكلية للمكتبة",
    "library_seats_count": "عدد المقاعد",
    "library_staff_count": "عدد موظفي المكتبة",
    "library_chairs_count": "عدد الكراسي",
    "curriculum_books_count": "عدد كتب المقررات",
    "digital_resources_count": "عدد المصادر الرقمية",
    "specialized_books_count": "عدد الكتب المتخصصة",
    "journals_references_count": "عدد الدوريات والمراجع",
    "library_staff_computers_count": "حواسيب موظفي المكتبة",
    "library_curriculum_books_count": "كتب المقررات في المكتبة",
    "library_specialist_staff_count": "عدد المختصين في المكتبة",
    "library_specialized_books_count": "الكتب المتخصصة في المكتبة",
    "library_electronic_sources_count": "المصادر الإلكترونية",
    "library_students_computers_count": "حواسيب الطلاب",
    "library_university_students_total": "إجمالي طلاب الجامعة",
    "life_skills": "المهارات الحياتية",
    "mental_skills": "المهارات الذهنية",
    "knowledge_skills": "المهارات المعرفية",
    "practical_skills": "المهارات العملية",
    "outcomesPreparationTable": "جدول إعداد المخرجات",
    "outcomes_preparation": "إعداد المخرجات",
    "outcomes_preparation[]": "إعداد المخرجات",
}


def _is_empty_value(value):
    return value in ("", None, [], {})


def _pretty_key(key):
    key = str(key).strip()
    return FIELD_LABELS.get(
        key,
        key.replace("_", " ").replace("[]", "").strip(),
    )


def _pretty_value(value):
    if value is True:
        return "نعم"
    if value is False:
        return "لا"
    return str(value)


def _flatten_form_data(value, parent_label=""):
    rows = []

    if isinstance(value, dict):
        for key, val in value.items():
            if _is_empty_value(val):
                continue

            label = _pretty_key(key)
            full_label = f"{parent_label} / {label}" if parent_label else label
            rows.extend(_flatten_form_data(val, full_label))

    elif isinstance(value, list):
        for index, item in enumerate(value, start=1):
            if _is_empty_value(item):
                continue

            item_label = (
                f"{parent_label} - بند {index}"
                if parent_label
                else f"بند {index}"
            )
            rows.extend(_flatten_form_data(item, item_label))

    else:
        if not _is_empty_value(value):
            rows.append((parent_label, _pretty_value(value)))

    return rows


def format_form_data(value):
    if not value:
        return mark_safe(
            '<span class="aq-empty-data">لا توجد بيانات مدخلة.</span>'
        )

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return format_html(
                """
                <div class="aq-json-view">
                    <div class="aq-json-row">
                        <strong>البيانات</strong>
                        <span>{}</span>
                    </div>
                </div>
                """,
                value,
            )

    rows = _flatten_form_data(value)

    if not rows:
        return mark_safe(
            '<span class="aq-empty-data">لا توجد بيانات مدخلة.</span>'
        )

    return format_html(
        '<div class="aq-json-view">{}</div>',
        format_html_join(
            "",
            """
            <div class="aq-json-row">
                <strong>{}</strong>
                <span>{}</span>
            </div>
            """,
            rows,
        ),
    )


def _readonly_model_fields(model, extra_fields=None):
    readonly = []

    for field in model._meta.fields:
        readonly.append(field.name)

    for field in model._meta.many_to_many:
        readonly.append(field.name)

    if extra_fields:
        for field_name in extra_fields:
            if field_name not in readonly:
                readonly.append(field_name)

    return readonly


# ==========================================================
# البحث العربي الذكي داخل لوحة الإدارة
# ==========================================================

ARABIC_DIACRITICS_RE = re.compile(
    r"[\u0617-\u061A\u064B-\u065F\u0670\u0640]"
)


def normalize_arabic_text(value):
    """
    توحيد النص العربي للبحث:
    أ/إ/آ -> ا
    ة -> ه
    ى -> ي
    ؤ -> و
    ئ -> ي
    مع حذف التشكيل والتطويل وتوحيد المسافات.
    """
    if value is None:
        return ""

    value = str(value).strip().lower()
    value = ARABIC_DIACRITICS_RE.sub("", value)

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ة": "ه",
        "ى": "ي",
        "ؤ": "و",
        "ئ": "ي",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return re.sub(r"\s+", " ", value)


def normalize_arabic_db_expression(expression):
    """تطبيع النص العربي على مستوى قاعدة البيانات."""
    expression = Cast(expression, output_field=CharField())
    expression = Coalesce(expression, Value(""))
    expression = Lower(expression)

    replacements = [
        ("أ", "ا"),
        ("إ", "ا"),
        ("آ", "ا"),
        ("ٱ", "ا"),
        ("ة", "ه"),
        ("ى", "ي"),
        ("ؤ", "و"),
        ("ئ", "ي"),
        ("ـ", ""),
    ]

    for old, new in replacements:
        expression = Replace(expression, Value(old), Value(new))

    return expression


class ArabicSmartSearchAdminMixin:
    """
    بحث عربي مرن داخل Django Admin:
    - يقبل اختلاف الهمزات.
    - يقبل جزءًا من النص.
    - يدعم علامة % كفاصل مرن.
    - يعمل على الحقول الموجودة داخل search_fields.
    """

    def get_search_results(self, request, queryset, search_term):
        original_queryset, use_distinct = super().get_search_results(
            request,
            queryset,
            search_term,
        )

        search_term = (search_term or "").strip()
        if not search_term:
            return original_queryset, use_distinct

        normalized_search = normalize_arabic_text(search_term)
        search_parts = [
            part
            for part in re.split(r"[\s%]+", normalized_search)
            if part
        ]

        if not search_parts:
            return original_queryset, use_distinct

        search_fields = (
            getattr(self, "arabic_search_fields", None)
            or self.search_fields
        )

        if not search_fields:
            return original_queryset, use_distinct

        annotations = {}
        normalized_field_names = []

        for index, field_name in enumerate(search_fields):
            clean_field_name = field_name.lstrip("^=@")
            annotation_name = f"_arabic_search_{index}"
            annotations[annotation_name] = normalize_arabic_db_expression(
                F(clean_field_name)
            )
            normalized_field_names.append(annotation_name)

        queryset = queryset.annotate(**annotations)
        final_query = Q()

        for part in search_parts:
            part_query = Q()

            for annotation_name in normalized_field_names:
                part_query |= Q(
                    **{f"{annotation_name}__icontains": part}
                )

            final_query &= part_query

        arabic_queryset = queryset.filter(final_query)
        return original_queryset | arabic_queryset, use_distinct


# ==========================================================
# ملفات التقييم - قراءة فقط
# ==========================================================

@admin.register(EvaluationFile)
class EvaluationFileAdmin(ArabicSmartSearchAdminMixin, admin.ModelAdmin):
    list_display = (
        "program",
        "academic_year",
        "status_text",
        "created_at",
        "updated_at",
        "open_file_link",
    )

    list_display_links = ("program",)

    fields = (
        "program",
        "academic_year",
        "status_text",
        "notes",
        "created_at",
        "updated_at",
    )

    readonly_fields = (
        "program",
        "academic_year",
        "status_text",
        "notes",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "program__name",
        "program__specialization",
        "academic_year",
    )

    ordering = (
        "-updated_at",
        "program__name",
        "-academic_year",
    )

    actions = None
    list_per_page = 24

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("program").exclude(
            status="template_preview"
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def get_readonly_fields(self, request, obj=None):
        return _readonly_model_fields(
            self.model,
            extra_fields=("status_text",),
        )


    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        total_files = self.get_queryset(request).count()
        extra_context["title"] = (
            f"ملفات البرامج الأكاديمية — عدد الملفات: {total_files}"
        )
        return super().changelist_view(
            request,
            extra_context=extra_context,
        )

    def change_view(
        self,
        request,
        object_id,
        form_url="",
        extra_context=None,
    ):
        extra_context = extra_context or {}
        extra_context["title"] = "عرض ملف تقييم"
        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context,
        )

    @admin.display(description="حالة الملف", ordering="status")
    def status_text(self, obj):
        return render_status_text(obj.status)

    @admin.display(description="الإجراء")
    def open_file_link(self, obj):
        url = f"/data-entry/?file_id={obj.id}"
        return format_html(
            """
            <a href="{}" class="aq-open-front-link">
                فتح في الواجهة
            </a>
            """,
            url,
        )


# ==========================================================
# معايير الجودة - إضافة وتعديل وحذف
# ==========================================================

@admin.register(QualityStandard)
class QualityStandardAdmin(ArabicSmartSearchAdminMixin, admin.ModelAdmin):
    list_display = (
        "number_display",
        "title_display",
        "weight_display",
        "is_active",
        "standard_actions",
    )

    list_display_links = None

    fields = (
        "number",
        "title",
        "weight",
        "is_active",
    )

    readonly_fields = ()
    search_fields = ("title",)
    list_filter = ()
    ordering = ("number",)
    actions = None
    list_per_page = 24

    def get_queryset(self, request):
        """
        تحميل سجلات بيانات المعيار ومرفقاتها مسبقًا؛
        حتى يظهر زر الحذف دون تنفيذ استعلامات متكررة لكل صف.
        """
        queryset = super().get_queryset(request)
        return queryset.prefetch_related(
            "entries__attachments"
        )

    @staticmethod
    def _value_contains_actual_data(value):
        """
        التحقق بصورة متداخلة من وجود قيمة فعلية داخل form_data.

        تعتبر القيم الفارغة والصفرية الافتراضية غير مدخلة،
        لأن بعض حقول الصفحة تُحفظ بصفر حتى بعد تفريغها.
        """
        if value is None:
            return False

        if isinstance(value, bool):
            return value

        if isinstance(value, dict):
            return any(
                QualityStandardAdmin._value_contains_actual_data(item)
                for item in value.values()
            )

        if isinstance(value, (list, tuple, set)):
            return any(
                QualityStandardAdmin._value_contains_actual_data(item)
                for item in value
            )

        if isinstance(value, (int, float)):
            return value != 0

        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized not in {
                "",
                "0",
                "0.0",
                "none",
                "null",
                "[]",
                "{}",
                "false",
            }

        return True

    def _entry_contains_actual_data(self, entry):
        """
        سجل StandardEntry يمنع حذف المعيار فقط عند وجود:
        - بيانات فعلية داخل form_data.
        - نسبة اكتمال أكبر من صفر.
        - مرفق واحد على الأقل.
        """
        has_form_data = self._value_contains_actual_data(
            entry.form_data or {}
        )

        has_completion = (
            entry.completion_percentage or 0
        ) > 0

        has_attachments = entry.attachments.exists()

        return (
            has_form_data
            or has_completion
            or has_attachments
        )

    def _standard_contains_actual_data(self, obj):
        """
        لا يكفي وجود سجل StandardEntry فارغ لمنع الحذف.
        المنع يكون فقط إذا احتوى أحد السجلات على بيانات فعلية.
        """
        return any(
            self._entry_contains_actual_data(entry)
            for entry in obj.entries.all()
        )

    def _can_delete_standard(self, request, obj):
        """
        يشترط امتلاك صلاحية حذف معيار الجودة،
        وألا تكون هناك بيانات فعلية مرتبطة بالمعيار.
        """
        if obj is None:
            return request.user.has_perm(
                "dashboard.delete_qualitystandard"
            )

        return (
            request.user.has_perm(
                "dashboard.delete_qualitystandard"
            )
            and not self._standard_contains_actual_data(obj)
        )

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return self._can_delete_standard(request, obj)

    def has_view_permission(self, request, obj=None):
        return True

    def get_readonly_fields(self, request, obj=None):
        return ()

    def get_deleted_objects(self, objs, request):
        """
        Django يمنع زر التأكيد لأن StandardEntryAdmin للعرض فقط،
        فيعتبر أن المستخدم لا يملك حذف «بيانات معيار» المرتبطة.

        عند كون تلك السجلات فارغة فعلًا، نزيل هذا المنع فقط؛
        أما أي نوع مرتبط آخر فيبقى خاضعًا لفحص Django المعتاد.
        """
        (
            deleted_objects,
            model_count,
            perms_needed,
            protected,
        ) = super().get_deleted_objects(objs, request)

        if all(
            self._can_delete_standard(request, obj)
            for obj in objs
        ):
            standard_entry_names = {
                str(StandardEntry._meta.verbose_name),
                str(StandardEntry._meta.verbose_name_plural),
            }

            perms_needed = {
                permission_name
                for permission_name in perms_needed
                if str(permission_name)
                not in standard_entry_names
            }

        return (
            deleted_objects,
            model_count,
            perms_needed,
            protected,
        )

    def delete_model(self, request, obj):
        """
        حذف سجلات StandardEntry الفارغة أولًا، ثم حذف المعيار.
        هذا لا يغيّر صلاحيات صفحة بيانات المعايير؛ تظل للعرض فقط.
        """
        if not self._can_delete_standard(request, obj):
            raise PermissionDenied(
                "لا يمكن حذف معيار مرتبط ببيانات فعلية."
            )

        obj.entries.all().delete()
        obj.delete()

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        total_standards = QualityStandard.objects.count()
        active_standards = QualityStandard.objects.filter(
            is_active=True
        ).count()
        extra_context["title"] = (
            "معايير الجودة"
            f" — عدد المعايير: {total_standards}"
            f" | النشطة: {active_standards}"
        )
        return super().changelist_view(
            request,
            extra_context=extra_context,
        )

    def change_view(
        self,
        request,
        object_id,
        form_url="",
        extra_context=None,
    ):
        extra_context = extra_context or {}
        extra_context["title"] = "تعديل معيار جودة"
        extra_context["show_save"] = True
        extra_context["show_save_and_continue"] = False
        extra_context["show_save_and_add_another"] = False
        extra_context["show_delete"] = False
        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context,
        )

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "إضافة معيار جودة"
        extra_context["show_save"] = True
        extra_context["show_save_and_continue"] = True
        extra_context["show_save_and_add_another"] = True
        extra_context["show_delete"] = False
        return super().add_view(
            request,
            form_url,
            extra_context,
        )

    def render_change_form(
        self,
        request,
        context,
        add=False,
        change=False,
        form_url="",
        obj=None,
    ):
        if add:
            context["show_save"] = True
            context["show_save_and_continue"] = True
            context["show_save_and_add_another"] = True
            context["show_delete"] = False
            context["has_delete_permission"] = False

        if change:
            context["show_save"] = True
            context["show_save_and_continue"] = False
            context["show_save_and_add_another"] = False
            context["show_delete"] = False
            context["has_delete_permission"] = False
            context["has_add_permission"] = False

        return super().render_change_form(
            request,
            context,
            add=add,
            change=change,
            form_url=form_url,
            obj=obj,
        )

    @admin.display(description="رقم المعيار", ordering="number")
    def number_display(self, obj):
        return format_html(
            '<span class="aq-strong-text">{}</span>',
            obj.number,
        )

    @admin.display(description="عنوان المعيار", ordering="title")
    def title_display(self, obj):
        return format_html(
            '<span class="aq-strong-text">{}</span>',
            obj.title,
        )

    @admin.display(description="الوزن النسبي", ordering="weight")
    def weight_display(self, obj):
        return format_html(
            '<span class="aq-strong-text">{}</span>',
            obj.weight,
        )

    @admin.display(description="الإجراءات")
    def standard_actions(self, obj):
        change_url = reverse(
            f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
            args=[obj.pk],
        )

        if self._standard_contains_actual_data(obj):
            return format_html(
                """
                <div class="aq-admin-actions">
                    <a href="{}" class="aq-action aq-action-edit">تعديل</a>
                    <span style="
                        color:#64748b;
                        font-size:11px;
                        font-weight:900;
                        white-space:nowrap;
                    ">
                        مرتبط ببيانات
                    </span>
                </div>
                """,
                change_url,
            )

        delete_url = reverse(
            f"admin:{obj._meta.app_label}_{obj._meta.model_name}_delete",
            args=[obj.pk],
        )

        return format_html(
            """
            <div class="aq-admin-actions">
                <a href="{}" class="aq-action aq-action-edit">تعديل</a>
                <a href="{}" class="aq-action aq-action-delete">حذف</a>
            </div>
            """,
            change_url,
            delete_url,
        )


# ==========================================================
# بيانات المعايير - قراءة فقط
# ==========================================================

@admin.register(StandardEntry)
class StandardEntryAdmin(ArabicSmartSearchAdminMixin, admin.ModelAdmin):
    list_display = (
        "evaluation_file",
        "standard",
        "completion_percentage",
        "completion_status_text",
        "evaluation_review_status_display",
        "created_at",
        "updated_at",
    )

    list_display_links = (
        "evaluation_file",
        "standard",
    )

    fields = (
        "evaluation_file",
        "standard",
        "completion_status_text",
        "completion_percentage",
        "evaluation_review_status_display",
        "formatted_form_data",
        "created_at",
        "updated_at",
    )

    readonly_fields = (
        "evaluation_file",
        "standard",
        "completion_status_text",
        "completion_percentage",
        "evaluation_review_status_display",
        "formatted_form_data",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "evaluation_file__program__name",
        "evaluation_file__program__specialization",
        "completion_status",
    )

    arabic_search_fields = (
        "evaluation_file__program__name",
        "evaluation_file__program__specialization",
        "completion_status",
    )

    ordering = (
        "-evaluation_file__updated_at",
        "evaluation_file__program__name",
        "-evaluation_file__academic_year",
        "standard__number",
    )

    actions = None
    list_per_page = 24

    def get_queryset(self, request):
        review_status_query = (
            StandardEvaluationReview.objects
            .filter(
                review__evaluation_file_id=OuterRef(
                    "evaluation_file_id"
                ),
                standard_id=OuterRef("standard_id"),
            )
            .order_by("-updated_at")
            .values("review_status")[:1]
        )

        return (
            super()
            .get_queryset(request)
            .select_related(
                "evaluation_file",
                "evaluation_file__program",
                "standard",
            )
            .filter(
                evaluation_file__status__in=[
                    "draft",
                    "in_progress",
                    "completed",
                ]
            )
            .annotate(
                actual_review_status=Subquery(
                    review_status_query
                )
            )
        )

    @admin.display(description="حالة التقييم")
    def evaluation_review_status_display(self, obj):
        status = getattr(
            obj,
            "actual_review_status",
            None,
        )

        if status == "reviewed":
            return mark_safe(
                '<span style="color:#16865c;font-weight:900;">'
                'معتمد'
                '</span>'
            )

        if status == "draft":
            return mark_safe(
                '<span style="color:#b77900;font-weight:900;">'
                'مسودة'
                '</span>'
            )

        return mark_safe(
            '<span style="color:#64748b;font-weight:800;">'
            'غير محفوظ'
            '</span>'
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def get_readonly_fields(self, request, obj=None):
        return _readonly_model_fields(
            self.model,
            extra_fields=(
                "completion_status_text",
                "evaluation_review_status_display",
                "formatted_form_data",
            ),
        )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request)
        total_entries = queryset.count()
        total_files = queryset.values(
            "evaluation_file_id"
        ).distinct().count()
        extra_context["title"] = (
            "بيانات المعايير"
            f" — عدد الملفات المحفوظة: {total_files}"
            f" | عدد سجلات المعايير: {total_entries}"
        )
        return super().changelist_view(
            request,
            extra_context=extra_context,
        )

    def change_view(
        self,
        request,
        object_id,
        form_url="",
        extra_context=None,
    ):
        extra_context = extra_context or {}
        extra_context["title"] = "عرض بيانات معيار"
        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context,
        )

    @admin.display(description="حالة الاكتمال", ordering="completion_status")
    def completion_status_text(self, obj):
        return render_status_text(obj.completion_status)

    @admin.display(description="بيانات الحقول العامة")
    def formatted_form_data(self, obj):
        return format_form_data(getattr(obj, "form_data", None))


# ==========================================================
# سجل نشاط المستخدمين - قراءة فقط
# ==========================================================

@admin.register(UserActivityLog)
class ActivityLogAdmin(ArabicSmartSearchAdminMixin, admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "action_label",
        "section",
        "standard_label",
        "object_repr",
        "ip_address",
    )

    list_filter = ()
    date_hierarchy = None
    actions = None

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "section",
        "standard_label",
        "model_name",
        "object_repr",
        "changes",
        "ip_address",
    )

    readonly_fields = (
        "created_at",
        "user",
        "action",
        "section",
        "standard_label",
        "model_name",
        "object_id",
        "object_repr",
        "changes",
        "ip_address",
        "user_agent",
        "url",
    )

    fields = readonly_fields
    ordering = ("-created_at",)
    list_per_page = 24

    class Media:
        css = {
            "all": ("admin/css/custom_admin_dashboard.css",),
        }

    @admin.display(description="نوع العملية")
    def action_label(self, obj):
        return obj.get_action_display()

    def get_actions(self, request):
        return {}

    def get_fieldsets(self, request, obj=None):
        return (
            (
                None,
                {
                    "fields": self.fields,
                },
            ),
        )

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ==========================================================
# إدارة المستخدمين بصورة مبسطة
# مجموعة واحدة فقط لكل مستخدم
# ==========================================================

class CleanUserChangeForm(UserChangeForm):
    group_choice = forms.ModelChoiceField(
    queryset=Group.objects.none(),
    required=False,
    label="المجموعة",
    empty_label="اختر المجموعة المناسبة",
    help_text="اختار المجموعة الوظيفية المناسبة للمستخدم.",
    widget=forms.Select(
        attrs={
            "class": "aq-group-select",
        }

    ),
)

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["group_choice"].queryset = (
            Group.objects.order_by("name")
        )

        if "username" in self.fields:
            self.fields["username"].help_text = ""

        self._original_group_ids = []
        self._original_permission_ids = []
        self._original_password = ""
        self._original_is_active = True
        self._original_is_staff = False
        self._original_is_superuser = False

        if self.instance and self.instance.pk:
            self._original_group_ids = list(
                self.instance.groups.values_list(
                    "pk",
                    flat=True,
                )
            )

            self._original_permission_ids = list(
                self.instance.user_permissions.values_list(
                    "pk",
                    flat=True,
                )
            )

            self._original_password = self.instance.password
            self._original_is_active = self.instance.is_active
            self._original_is_staff = self.instance.is_staff
            self._original_is_superuser = self.instance.is_superuser

            current_group = (
                self.instance.groups
                .order_by("name")
                .first()
            )

            if current_group:
                self.fields["group_choice"].initial = (
                    current_group.pk
                )


class CleanUserCreationForm(UserCreationForm):
    group_choice = forms.ModelChoiceField(
    queryset=Group.objects.none(),
    required=False,
    label="المجموعة",
    empty_label="اختر المجموعة المناسبة",
    help_text="اختار المجموعة الوظيفية المناسبة للمستخدم.",
    widget=forms.Select(
        attrs={
            "class": "aq-group-select",
            
        }

    ),
)

    class Meta(UserCreationForm.Meta):
        model = User

        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["group_choice"].queryset = (
            Group.objects.order_by("name")
        )

        if "username" in self.fields:
            self.fields["username"].help_text = ""


try:
    admin.site.unregister(User)
except NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(DefaultUserAdmin):
    form = CleanUserChangeForm
    add_form = CleanUserCreationForm

    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "group_display",
        "is_active",
        "is_staff",
    )

    list_filter = ()

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "groups__name",
    )

    ordering = ("username",)

    fieldsets = (
        (
            "بيانات الحساب",
            {
                "fields": (
                    "username",
                    "password_reset_link",
                )
            },
        ),
        (
            "المعلومات الشخصية",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                )
            },
        ),
        (
            "صلاحيات الدخول",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
                "description": (
                    "فعّلي حالة الطاقم فقط إذا كان المستخدم "
                    "يحتاج الدخول إلى لوحة الإدارة، ولا تفعّلي "
                    "المستخدم الفائق للحسابات العادية."
                ),
            },
        ),
        (
            "المجموعة الوظيفية",
            {
                "fields": (
                    "group_choice",
                ),
                "description": (
                    "اختاري مجموعة واحدة ليحصل المستخدم "
                    "على الصلاحيات المحددة داخلها."
                ),
            },
        ),
    )

    readonly_fields = (
        "password_reset_link",
    )

    add_fieldsets = (
        (
            "إنشاء مستخدم جديد",
            {
                "classes": (
                    "wide",
                ),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "email",
                    "is_active",
                    "group_choice",
                ),
            },
        ),
    )

    # يجب أن يبقى فارغًا حتى لا يظهر نظام العمودين.
    filter_horizontal = ()

    actions = None

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        return queryset.prefetch_related(
            "groups"
        )

    @admin.display(
        description="المجموعة",
    )
    def group_display(self, obj):
        group = (
            obj.groups
            .order_by("name")
            .first()
        )

        if group:
            return group.name

        return "بدون مجموعة"

    @admin.display(
        description="كلمة المرور",
    )
    def password_reset_link(self, obj):
        if not obj or not obj.pk:
            return (
                "احفظي المستخدم أولًا ثم يمكنك "
                "تغيير كلمة المرور."
            )

        url = reverse(
            "admin:auth_user_password_change",
            args=[
                obj.pk,
            ],
        )

        return format_html(
            """
            <a href="{}" class="ust-password-reset-btn">
                إعادة ضبط كلمة المرور
            </a>
            """,
            url,
        )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        """
        حفظ المستخدم بصورة آمنة.

        عند فتح صفحة تغيير اسم المستخدم فقط عبر:
        ?edit_username=1

        يتم تغيير username وحده مع الحفاظ على:
        - كلمة المرور المشفرة.
        - حالة الحساب.
        - صلاحية دخول لوحة الإدارة.
        - صلاحية المستخدم الفائق.
        """

        username_only_edit = (
            change
            and request.GET.get("edit_username") == "1"
        )

        if username_only_edit:
            obj.password = getattr(
                form,
                "_original_password",
                obj.password,
            )

            obj.is_active = getattr(
                form,
                "_original_is_active",
                obj.is_active,
            )

            obj.is_staff = getattr(
                form,
                "_original_is_staff",
                obj.is_staff,
            )

            obj.is_superuser = getattr(
                form,
                "_original_is_superuser",
                obj.is_superuser,
            )

        super().save_model(
            request,
            obj,
            form,
            change,
        )

    def save_related(
        self,
        request,
        form,
        formsets,
        change,
    ):
        """
        حفظ العلاقات والصلاحيات دون حذفها عند تغيير الاسم فقط.
        """

        username_only_edit = (
            change
            and request.GET.get("edit_username") == "1"
        )

        original_group_ids = list(
            getattr(
                form,
                "_original_group_ids",
                [],
            )
        )

        original_permission_ids = list(
            getattr(
                form,
                "_original_permission_ids",
                [],
            )
        )

        super().save_related(
            request,
            form,
            formsets,
            change,
        )

        # تغيير اسم المستخدم فقط:
        # نعيد المجموعات والصلاحيات كما كانت تمامًا.
        if username_only_edit:
            form.instance.groups.set(
                original_group_ids
            )

            form.instance.user_permissions.set(
                original_permission_ids
            )

            return

        selected_group = form.cleaned_data.get(
            "group_choice"
        )

        # إنشاء مستخدم جديد.
        if not change:
            if selected_group:
                form.instance.groups.set([
                    selected_group
                ])
            else:
                form.instance.groups.clear()

            return

        # تعديل المجموعة فقط إذا غيّرها المستخدم فعليًا.
        if "group_choice" in form.changed_data:
            if selected_group:
                form.instance.groups.set([
                    selected_group
                ])
            else:
                form.instance.groups.clear()

            return

        # تعديل اسم أو بريد أو بيانات أخرى:
        # المحافظة على المجموعة السابقة.
        form.instance.groups.set(
            original_group_ids
        )

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False
# ضعي هذا الجزء في ملف admin.py الذي يحتوي تخصيصات لوحة الإدارة.
# يمنع ظهور صلاحيات النماذج المحذوفة أو غير المعروضة في لوحة الإدارة.

from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


class CleanGroupAdmin(GroupAdmin):
    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "permissions":
            registered_models = tuple(self.admin_site._registry.keys())

            registered_content_types = ContentType.objects.get_for_models(
                *registered_models,
                for_concrete_models=False,
            )

            allowed_content_type_ids = [
                content_type.pk
                for model, content_type in registered_content_types.items()
                if model._meta.label_lower not in {
                    "contenttypes.contenttype",
                    "sessions.session",
                    "auth.permission",
                }
            ]

            permissions = (
                Permission.objects
                .filter(content_type_id__in=allowed_content_type_ids)
                .exclude(
                    Q(
                        content_type__app_label="admin",
                        content_type__model="logentry",
                    )
                    & ~Q(codename="view_logentry")
                )
                .select_related("content_type")
                .order_by(
                    "content_type__app_label",
                    "content_type__model",
                    "codename",
                )
            )

            kwargs["queryset"] = permissions

        return super().formfield_for_manytomany(
            db_field,
            request=request,
            **kwargs,
        )


try:
    admin.site.unregister(Group)
except NotRegistered:
    pass

admin.site.register(Group, CleanGroupAdmin)
