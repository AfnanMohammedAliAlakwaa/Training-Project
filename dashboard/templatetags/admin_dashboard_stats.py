from datetime import datetime, date, time

from django import template
from django.apps import apps
from django.db.models import Q
from django.utils import timezone

register = template.Library()


def _get_model(app_label, model_name):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


def _safe_count(model):
    if model is None:
        return 0

    try:
        return model.objects.count()
    except Exception:
        return 0


def _safe_queryset_count(queryset):
    if queryset is None:
        return 0

    try:
        return queryset.count()
    except Exception:
        return 0


def _field_exists(model, field_name):
    if model is None:
        return False

    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _first_existing_field(model, field_names):
    if model is None:
        return None

    for field_name in field_names:
        if _field_exists(model, field_name):
            return field_name

    return None


def _build_status_query(field_name, values):
    query = Q()

    if not field_name:
        return query

    for value in values:
        query |= Q(**{f"{field_name}__iexact": value})

    return query


def _count_status_values_from_queryset(queryset, field_name, values):
    if queryset is None or not field_name:
        return 0

    try:
        query = _build_status_query(field_name, values)

        if not query:
            return 0

        return queryset.filter(query).count()
    except Exception:
        return 0


def _latest_date_from_model(model, field_names):
    if model is None:
        return None

    field_name = _first_existing_field(model, field_names)

    if not field_name:
        return None

    try:
        obj = (
            model.objects
            .exclude(**{f"{field_name}__isnull": True})
            .order_by(f"-{field_name}")
            .first()
        )

        if not obj:
            return None

        return getattr(obj, field_name, None)
    except Exception:
        return None


def _latest_date_from_queryset(queryset, model, field_names):
    if queryset is None or model is None:
        return None

    field_name = _first_existing_field(model, field_names)

    if not field_name:
        return None

    try:
        obj = (
            queryset
            .exclude(**{f"{field_name}__isnull": True})
            .order_by(f"-{field_name}")
            .first()
        )

        if not obj:
            return None

        return getattr(obj, field_name, None)
    except Exception:
        return None


def _to_datetime(value):
    if not value:
        return None

    try:
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, date):
            dt = datetime.combine(value, time.min)
        else:
            return None

        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())

        return timezone.localtime(dt)
    except Exception:
        return None


def _format_ar_date(value):
    dt = _to_datetime(value)

    if not dt:
        return "لا يوجد"

    try:
        return dt.strftime("%Y/%m/%d")
    except Exception:
        return "لا يوجد"


def _get_clean_evaluation_files_queryset(EvaluationFile, status_field):
    """
    يحسب ملفات التقييم الفعلية فقط.

    يستبعد:
    - ملفات المعاينة template_preview
    - أي ملف بدون برنامج إن وجد
    """

    if EvaluationFile is None:
        return None

    try:
        queryset = EvaluationFile.objects.all()

        if _field_exists(EvaluationFile, "program"):
            queryset = queryset.exclude(program__isnull=True)

        if status_field:
            preview_query = _build_status_query(
                status_field,
                [
                    "template_preview",
                    "preview",
                    "معاينة",
                    "معاينة قالب",
                ],
            )

            if preview_query:
                queryset = queryset.exclude(preview_query)

        return queryset

    except Exception:
        return None


def _get_clean_standard_entries_queryset(StandardEntry, evaluation_files_queryset):
    """
    يحسب سجلات بيانات المعايير الفعلية فقط.

    إذا كان StandardEntry مرتبطًا بملف تقييم، نحسب السجلات التابعة
    لملفات التقييم النظيفة فقط.
    """

    if StandardEntry is None:
        return None

    try:
        queryset = StandardEntry.objects.all()

        file_field = _first_existing_field(
            StandardEntry,
            [
                "evaluation_file",
                "file",
                "evaluation",
            ],
        )

        if file_field and evaluation_files_queryset is not None:
            queryset = queryset.filter(**{
                f"{file_field}__in": evaluation_files_queryset
            })

        return queryset

    except Exception:
        return None


@register.simple_tag
def get_admin_dashboard_stats():
    Program = _get_model("programs", "Program")
    EvaluationFile = _get_model("dashboard", "EvaluationFile")
    QualityStandard = _get_model("dashboard", "QualityStandard")
    StandardEntry = _get_model("dashboard", "StandardEntry")

    programs_total = _safe_count(Program)
    quality_standards_total = _safe_count(QualityStandard)

    status_field = _first_existing_field(
        EvaluationFile,
        [
            "status",
            "file_status",
            "evaluation_status",
            "state",
            "completion_status",
        ],
    )

    evaluation_files_queryset = _get_clean_evaluation_files_queryset(
        EvaluationFile,
        status_field,
    )

    evaluation_files_total = _safe_queryset_count(evaluation_files_queryset)

    standard_entries_queryset = _get_clean_standard_entries_queryset(
        StandardEntry,
        evaluation_files_queryset,
    )

    # هذا هو الرقم الذي سيظهر في كرت "بيانات المعايير"
    # ويطابق "عدد سجلات المعايير" في صفحة بيانات المعايير.
    standard_entries_total = _safe_queryset_count(standard_entries_queryset)

    completed_files = _count_status_values_from_queryset(
        evaluation_files_queryset,
        status_field,
        [
            "مكتمل",
            "مكتملة",
            "complete",
            "completed",
            "done",
            "finished",
        ],
    )

    if evaluation_files_total:
        incomplete_files = max(evaluation_files_total - completed_files, 0)
        readiness_percent = round((completed_files / evaluation_files_total) * 100)
    else:
        incomplete_files = 0
        readiness_percent = 0

    if readiness_percent >= 90:
        readiness_label = "جاهزية ممتازة"
    elif readiness_percent >= 70:
        readiness_label = "جاهزية جيدة"
    elif readiness_percent >= 40:
        readiness_label = "بحاجة إلى متابعة"
    else:
        readiness_label = "بحاجة إلى استكمال"

    latest_dates_raw = [
        _latest_date_from_queryset(
            evaluation_files_queryset,
            EvaluationFile,
            ["updated_at", "modified_at", "updated", "last_update", "created_at", "created"],
        ),
        _latest_date_from_queryset(
            standard_entries_queryset,
            StandardEntry,
            ["updated_at", "modified_at", "updated", "last_update", "created_at", "created"],
        ),
        _latest_date_from_model(
            QualityStandard,
            ["updated_at", "modified_at", "updated", "last_update", "created_at", "created"],
        ),
        _latest_date_from_model(
            Program,
            ["updated_at", "modified_at", "updated", "last_update", "created_at", "created"],
        ),
    ]

    latest_dates = [_to_datetime(value) for value in latest_dates_raw]
    latest_dates = [value for value in latest_dates if value]

    latest_update = max(latest_dates) if latest_dates else None

    return {
        "programs_total": programs_total,
        "evaluation_files_total": evaluation_files_total,
        "quality_standards_total": quality_standards_total,
        "standard_entries_total": standard_entries_total,
        "completed_files": completed_files,
        "incomplete_files": incomplete_files,
        "readiness_percent": readiness_percent,
        "readiness_label": readiness_label,
        "latest_update": _format_ar_date(latest_update),
    }