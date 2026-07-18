import re

from django.contrib import admin
from django.db.models import CharField, F, Q, Value
from django.db.models.functions import Cast, Coalesce, Lower, Replace
from django.urls import reverse
from django.utils.html import format_html

from .models import Program


def model_has_lookup(model, lookup):
    current_model = model

    for part in lookup.split("__"):
        try:
            field = current_model._meta.get_field(part)
        except Exception:
            return False

        related_model = getattr(field, "related_model", None)
        if related_model is not None:
            current_model = related_model

    return True


def existing_fields(model, candidates):
    return tuple(
        field_name
        for field_name in candidates
        if model_has_lookup(model, field_name)
    )


ARABIC_DIACRITICS_RE = re.compile(
    r"[\u0617-\u061A\u064B-\u0652\u0670\u0640]"
)


def normalize_arabic_text(value):
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

    return value


def normalize_arabic_db_expression(expression):
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
    def get_arabic_search_fields(self, request):
        return self.get_search_fields(request)

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

        search_fields = self.get_arabic_search_fields(request)
        annotations = {}
        normalized_field_names = []

        for index, field_name in enumerate(search_fields):
            clean_field_name = field_name.lstrip("^=@")

            if not model_has_lookup(self.model, clean_field_name):
                continue

            annotation_name = f"_arabic_search_{index}"
            annotations[annotation_name] = normalize_arabic_db_expression(
                F(clean_field_name)
            )
            normalized_field_names.append(annotation_name)

        if not annotations:
            return original_queryset, use_distinct

        normalized_queryset = queryset.annotate(**annotations)
        final_query = Q()

        for part in search_parts:
            part_query = Q()

            for annotation_name in normalized_field_names:
                part_query |= Q(
                    **{f"{annotation_name}__icontains": part}
                )

            final_query &= part_query

        arabic_queryset = normalized_queryset.filter(final_query)
        return (original_queryset | arabic_queryset).distinct(), True


@admin.register(Program)
class ProgramAdmin(ArabicSmartSearchAdminMixin, admin.ModelAdmin):
    actions = None
    list_display_links = None
    list_filter = ()
    list_per_page = 24

    def get_fields(self, request, obj=None):
        # تظهر هذه الحقول فقط في صفحتي الإضافة والتعديل.
        return existing_fields(
            self.model,
            (
                "name",
                "specialization",
                "start_year",
            ),
        )

    def get_list_display(self, request):
        # تظهر هذه الأعمدة فقط في صفحة قائمة البرامج.
        display_fields = ["name_display"]

        if model_has_lookup(self.model, "specialization"):
            display_fields.append("specialization_display")

        if model_has_lookup(self.model, "start_year"):
            display_fields.append("start_year_display")

        display_fields.append("program_actions")
        return tuple(display_fields)

    def get_list_filter(self, request):
        return ()

    def get_search_fields(self, request):
        return existing_fields(
            self.model,
            (
                "name",
                "specialization",
            ),
        )

    def get_arabic_search_fields(self, request):
        return self.get_search_fields(request)

    def get_ordering(self, request):
        ordering = []

        if model_has_lookup(self.model, "name"):
            ordering.append("name")

        if model_has_lookup(self.model, "specialization"):
            ordering.append("specialization")

        if model_has_lookup(self.model, "start_year"):
            ordering.append("start_year")

        return tuple(ordering) or ("pk",)

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request,
            queryset,
            search_term,
        )

        search_term = (search_term or "").strip()

        if (
            search_term.isdigit()
            and model_has_lookup(self.model, "start_year")
        ):
            queryset = (
                queryset
                | self.model.objects.filter(start_year=int(search_term))
            ).distinct()

        return queryset, use_distinct

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        total_programs = self.model.objects.count()
        extra_context["title"] = (
            f"البرامج الأكاديمية — عدد البرامج: {total_programs}"
        )

        return super().changelist_view(
            request,
            extra_context=extra_context,
        )

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "إضافة برنامج أكاديمي"
        extra_context["show_save"] = True
        extra_context["show_save_and_continue"] = True
        extra_context["show_save_and_add_another"] = True
        extra_context["show_delete"] = False

        return super().add_view(
            request,
            form_url,
            extra_context,
        )

    def change_view(
        self,
        request,
        object_id,
        form_url="",
        extra_context=None,
    ):
        extra_context = extra_context or {}
        extra_context["title"] = "تعديل برنامج أكاديمي"
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

        return super().render_change_form(
            request,
            context,
            add=add,
            change=change,
            form_url=form_url,
            obj=obj,
        )

    @admin.display(description="اسم البرنامج", ordering="name")
    def name_display(self, obj):
        return format_html(
            '<span class="aq-strong-text">{}</span>',
            getattr(obj, "name", ""),
        )

    @admin.display(description="التخصص", ordering="specialization")
    def specialization_display(self, obj):
        value = getattr(obj, "specialization", None) or "عام / بدون تخصص"
        return format_html(
            '<span class="aq-strong-text">{}</span>',
            value,
        )

    @admin.display(description="سنة الإنشاء", ordering="start_year")
    def start_year_display(self, obj):
        value = getattr(obj, "start_year", None)
        return format_html(
            '<span class="aq-strong-text">{}</span>',
            value or "غير محددة",
        )

    @admin.display(description="الإجراءات")
    def program_actions(self, obj):
        change_url = reverse(
            f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
            args=[obj.pk],
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
