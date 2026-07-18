import re
from decimal import Decimal, ROUND_HALF_UP

from django.apps import apps
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.urls import reverse

from dashboard.models import (
    AcademicProgram,
    EvaluationFile,
    GraduateRecord,
    StandardEntry,
    StudentLevelCount,
)
from improvements.models import ImprovementPlan

from .evaluation_service import (
    generate_auto_review,
    score_label,
)
from .models import ProgramEvaluationReview


# ============================================================
# أدوات عامة
# ============================================================

def _current_user_or_none(request):
    if hasattr(request, "user") and request.user.is_authenticated:
        return request.user
    return None


def _as_decimal(value):
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _as_float(value):
    return float(_as_decimal(value))


def _round_decimal(value):
    return _as_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _percentage(part, total):
    if not total:
        return 0
    return round((part / total) * 100, 2)


def _extract_year_start(value):
    value = str(value or "").strip()
    digits = ""

    for char in value:
        if char.isdigit():
            digits += char
            if len(digits) == 4:
                break

    if len(digits) == 4:
        return int(digits)

    return 0


def _status_label(status):
    labels = {
        "empty": "بحاجة إلى مراجعة",
        "draft": "مسودة",
        "reviewed": "معتمد",
        "aggregate": "متوسط النطاق",
    }
    return labels.get(status, "بحاجة إلى مراجعة")


def _status_class(status):
    classes = {
        "empty": "is-empty",
        "draft": "is-draft",
        "reviewed": "is-reviewed",
        "aggregate": "is-draft",
    }
    return classes.get(status, "is-empty")


def _risk_info(percentage, status=None):
    """
    تحديد مستوى الخطورة بناءً على نسبة الأداء فقط.

    حالة المراجعة مثل:
    - بحاجة إلى مراجعة
    - مسودة
    - معتمد

    تظهر بصورة مستقلة، ولا تغيّر مستوى الخطورة.
    """
    percentage = _as_decimal(percentage)

    if percentage >= 80:
        return {
            "label": "منخفضة",
            "class": "risk-low",
            "note": "المعيار في وضع جيد.",
        }

    if percentage >= 50:
        return {
            "label": "متوسطة",
            "class": "risk-medium",
            "note": "يحتاج المعيار متابعة وتحسين.",
        }

    return {
        "label": "مرتفعة",
        "class": "risk-high",
        "note": "المعيار يحتاج تدخلًا عاجلًا.",
    }

def _performance_class_by_percentage(percentage):
    percentage = _as_decimal(percentage)

    if percentage >= 80:
        return "is-good"

    if percentage >= 50:
        return "is-medium"

    return "is-weak"


def _css_width_value(percentage):
    value = _as_float(percentage)

    if value < 0:
        value = 0

    if value > 100:
        value = 100

    return f"{value:.2f}"

def _quality_label(percentage):
    percentage = _as_decimal(percentage)

    if percentage >= 90:
        return "ممتاز"
    if percentage >= 80:
        return "جيد جدًا"
    if percentage >= 65:
        return "جيد"
    if percentage >= 50:
        return "يحتاج تحسين"
    return "منخفض"


def _get_final_percentage(standard_review):
    if standard_review.reviewer_percentage is not None:
        return standard_review.reviewer_percentage
    return standard_review.auto_percentage


def _get_final_score(standard_review):
    if standard_review.reviewer_score is not None:
        return standard_review.reviewer_score
    return standard_review.auto_score


def _program_name(review):
    if not review or not review.evaluation_file:
        return "برنامج غير محدد"

    return str(review.evaluation_file.program)


def _academic_year(review):
    if not review or not review.evaluation_file:
        return "غير محدد"

    return str(review.evaluation_file.academic_year)


# ============================================================
# خيارات الفلترة
# ============================================================

def _get_academic_year_options():
    years = (
        EvaluationFile.objects
        .exclude(status="template_preview")
        .exclude(academic_year="")
        .values_list("academic_year", flat=True)
        .distinct()
    )

    years = list(years)

    years.sort(
        key=lambda value: _extract_year_start(value),
        reverse=True,
    )

    return years



_ARABIC_PROGRAM_DIACRITICS_RE = re.compile(
    r"[\u0617-\u061A\u064B-\u065F\u0670\u0640]"
)

_ARABIC_PROGRAM_NORMALIZATION = str.maketrans({
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ٱ": "ا",
    "ؤ": "و",
    "ئ": "ي",
    "ى": "ي",
    "ة": "ه",
    "ـ": "",
    "–": "-",
    "—": "-",
})


def _normalize_program_text(value):
    """
    توحيد أسماء البرامج قبل المقارنة، مع معالجة:
    - اختلافات الهمزات.
    - التاء المربوطة والألف المقصورة.
    - التشكيل والتطويل.
    - اختلاف المسافات حول الشرطة.
    """
    text = str(value or "").strip().casefold()
    text = _ARABIC_PROGRAM_DIACRITICS_RE.sub("", text)
    text = text.translate(_ARABIC_PROGRAM_NORMALIZATION)
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _program_display_name(program):
    """
    إنشاء الاسم الذي يظهر للمستخدم دون تكرار التخصص إذا كان
    مكتوبًا أصلًا داخل اسم البرنامج.
    """
    if not program:
        return ""

    name = str(
        getattr(program, "name", "") or ""
    ).strip()

    specialization = str(
        getattr(program, "specialization", "") or ""
    ).strip()

    if not specialization:
        return name

    normalized_name = _normalize_program_text(name)
    normalized_specialization = _normalize_program_text(
        specialization
    )

    if (
        normalized_specialization
        and normalized_specialization in normalized_name
    ):
        return name

    return f"{name} - {specialization}"


def _program_identity_key(program):
    """
    مفتاح موحد للبرنامج يستخدم الاسم النهائي الظاهر في القائمة.

    بهذا تُدمج الحالات التالية باعتبارها برنامجًا واحدًا:
    - أمن سيبراني / أمن سيبراني.
    - إلكترونية / الكترونية.
    - الاسم مع تخصص منفصل أو الاسم الذي يتضمن التخصص داخله.
    """
    normalized_display_name = _normalize_program_text(
        _program_display_name(program)
    )

    if not normalized_display_name:
        return ("", "")

    return (normalized_display_name, "")


def _model_has_field(model, field_name):
    """التحقق من وجود حقل داخل الموديل دون افتراض بنيته."""
    return any(
        field.name == field_name
        for field in model._meta.get_fields()
    )


def _clean_program_value(value):
    """تنظيف القيم النصية القادمة من جدول البرامج الرئيسي."""
    if value is None:
        return ""

    value = str(value).strip()

    if value.casefold() in {
        "",
        "none",
        "null",
        "nan",
    }:
        return ""

    return value


def _source_program_display_name(program):
    """
    بناء الاسم النهائي لبرنامج موجود في programs.Program.

    تدعم الدالة وجود التخصص في حقل مستقل أو داخل الاسم نفسه.
    """
    name = _clean_program_value(
        getattr(program, "name", "")
    )

    specialization = _clean_program_value(
        getattr(program, "specialization", "")
    )

    if specialization in {
        "لا يوجد",
        "غير محدد",
        "غير محددة",
        "-",
    }:
        specialization = ""

    if not specialization:
        return name

    normalized_name = _normalize_program_text(name)
    normalized_specialization = _normalize_program_text(
        specialization
    )

    if (
        normalized_specialization
        and normalized_specialization in normalized_name
    ):
        return name

    return f"{name} - {specialization}"


def _source_program_identity_key(program):
    """مفتاح موحد لبرنامج جدول البرامج الرئيسي."""
    display_name = _source_program_display_name(program)
    return _normalize_program_text(display_name)


def _source_program_is_active(program):
    """قراءة حالة البرنامج مهما كان اسم حقل النشاط."""
    if hasattr(program, "is_active"):
        return bool(program.is_active)

    if hasattr(program, "active"):
        return bool(program.active)

    return True


def _source_program_start_year(program):
    """قراءة سنة بداية البرنامج من الأسماء المحتملة للحقل."""
    for field_name in (
        "start_year",
        "establishment_year",
        "created_year",
        "year",
    ):
        if not hasattr(program, field_name):
            continue

        value = getattr(program, field_name)

        if value in (None, ""):
            continue

        try:
            return int(value)
        except (TypeError, ValueError):
            continue

    return None


def _sync_master_program_catalog():
    """
    مزامنة البرامج التي تُدار من programs.Program مع AcademicProgram.

    السلوك:
    - يضيف البرامج الجديدة إلى AcademicProgram.
    - يعيد تفعيل البرنامج إذا أُضيف مرة أخرى بعد حذفه سابقًا.
    - يعطّل البرامج التي حُذفت من programs.Program حتى تختفي من التحليل.
    - لا يحذف السجلات فعليًا، حفاظًا على أي ملفات تقييم تاريخية مرتبطة بها.

    ترجع الدالة مجموعة المفاتيح الحالية في جدول البرامج الرئيسي.
    """
    try:
        ProgramCatalog = apps.get_model(
            "programs",
            "Program",
        )
    except LookupError:
        return None

    source_queryset = ProgramCatalog.objects.all()

    if _model_has_field(ProgramCatalog, "is_active"):
        source_queryset = source_queryset.filter(
            is_active=True
        )
    elif _model_has_field(ProgramCatalog, "active"):
        source_queryset = source_queryset.filter(
            active=True
        )

    source_programs = list(source_queryset)

    source_by_key = {}

    for source_program in source_programs:
        source_key = _source_program_identity_key(
            source_program
        )

        if not source_key:
            continue

        source_by_key[source_key] = source_program

    source_keys = set(source_by_key.keys())

    existing_programs = list(
        AcademicProgram.objects.all()
    )

    existing_by_key = {}

    for academic_program in existing_programs:
        key = _normalize_program_text(
            _program_display_name(academic_program)
        )

        if not key:
            continue

        existing_by_key.setdefault(
            key,
            [],
        ).append(academic_program)

    with transaction.atomic():
        # إضافة البرامج الجديدة وتحديث البرامج الموجودة.
        for source_key, source_program in source_by_key.items():
            name = _clean_program_value(
                getattr(source_program, "name", "")
            )

            if not name:
                continue

            specialization = _clean_program_value(
                getattr(
                    source_program,
                    "specialization",
                    "",
                )
            )

            if specialization in {
                "لا يوجد",
                "غير محدد",
                "غير محددة",
                "-",
            }:
                specialization = ""

            matching_rows = existing_by_key.get(
                source_key,
                [],
            )

            if not matching_rows:
                create_values = {
                    "name": name,
                    "specialization": specialization,
                }

                if _model_has_field(
                    AcademicProgram,
                    "is_active",
                ):
                    create_values["is_active"] = True

                start_year = _source_program_start_year(
                    source_program
                )

                if (
                    start_year is not None
                    and _model_has_field(
                        AcademicProgram,
                        "start_year",
                    )
                ):
                    create_values["start_year"] = start_year

                created_program = AcademicProgram.objects.create(
                    **create_values
                )

                existing_by_key[source_key] = [
                    created_program
                ]

                continue

            # إعادة تفعيل السجلات المطابقة، مع تحديث السجل الأساسي.
            matching_rows.sort(
                key=lambda program: int(
                    getattr(program, "id", 0) or 0
                )
            )

            primary_program = matching_rows[0]
            changed_fields = []

            if getattr(primary_program, "name", "") != name:
                primary_program.name = name
                changed_fields.append("name")

            if (
                getattr(
                    primary_program,
                    "specialization",
                    "",
                ) or ""
            ) != specialization:
                primary_program.specialization = specialization
                changed_fields.append("specialization")

            start_year = _source_program_start_year(
                source_program
            )

            if (
                start_year is not None
                and _model_has_field(
                    AcademicProgram,
                    "start_year",
                )
                and getattr(
                    primary_program,
                    "start_year",
                    None,
                ) != start_year
            ):
                primary_program.start_year = start_year
                changed_fields.append("start_year")

            if (
                _model_has_field(
                    AcademicProgram,
                    "is_active",
                )
                and not bool(
                    getattr(
                        primary_program,
                        "is_active",
                        True,
                    )
                )
            ):
                primary_program.is_active = True
                changed_fields.append("is_active")

            if changed_fields:
                primary_program.save(
                    update_fields=list(
                        dict.fromkeys(changed_fields)
                    )
                )

            # أي نسخة مكررة لنفس البرنامج تبقى غير ظاهرة.
            if (
                _model_has_field(
                    AcademicProgram,
                    "is_active",
                )
                and len(matching_rows) > 1
            ):
                duplicate_ids = [
                    program.id
                    for program in matching_rows[1:]
                    if bool(
                        getattr(
                            program,
                            "is_active",
                            True,
                        )
                    )
                ]

                if duplicate_ids:
                    AcademicProgram.objects.filter(
                        id__in=duplicate_ids
                    ).update(
                        is_active=False
                    )

        # تعطيل أي برنامج لم يعد موجودًا في جدول البرامج الرئيسي.
        if _model_has_field(
            AcademicProgram,
            "is_active",
        ):
            stale_ids = []

            for academic_program in AcademicProgram.objects.all():
                key = _normalize_program_text(
                    _program_display_name(
                        academic_program
                    )
                )

                if (
                    key
                    and key not in source_keys
                    and bool(
                        getattr(
                            academic_program,
                            "is_active",
                            True,
                        )
                    )
                ):
                    stale_ids.append(
                        academic_program.id
                    )

            if stale_ids:
                AcademicProgram.objects.filter(
                    id__in=stale_ids
                ).update(
                    is_active=False
                )

    return source_keys

def _evaluation_file_counts_by_program():
    """
    عدد ملفات التقييم الفعلية لكل سجل برنامج.

    يستخدم عند اختيار السجل الأساسي بين السجلات المتكررة،
    حتى نحافظ على السجل المرتبط بالبيانات الحقيقية.
    """
    rows = (
        EvaluationFile.objects
        .exclude(status="template_preview")
        .values("program_id")
        .annotate(total=Count("id"))
        .values_list("program_id", "total")
    )

    return {
        program_id: total
        for program_id, total in rows
        if program_id
    }


def _program_preference_key(program, evaluation_counts=None):
    """
    ترتيب الأفضلية عند وجود سجلات متكررة:

    1. السجل النشط.
    2. السجل المرتبط بأكبر عدد من ملفات التقييم.
    3. الصياغة العربية المفضلة.
    4. السجل الأقدم لضمان ثبات المعرف المختار.
    """
    evaluation_counts = evaluation_counts or {}

    name = str(
        getattr(program, "name", "") or ""
    )

    specialization = str(
        getattr(program, "specialization", "") or ""
    )

    full_text = f"{name} {specialization}"

    contains_unwanted_spelling = (
        "إلكترونية" in full_text
        or "الإلكترونية" in full_text
    )

    is_active = bool(
        getattr(program, "is_active", True)
    )

    evaluation_count = int(
        evaluation_counts.get(program.id, 0) or 0
    )

    return (
        0 if is_active else 1,
        -evaluation_count,
        1 if contains_unwanted_spelling else 0,
        int(getattr(program, "id", 0) or 0),
    )


def _get_canonical_program_data():
    """
    تجهيز مصدر موحد للبرامج دون تكرار.

    المصدر الرئيسي هو programs.Program:
    - البرنامج الموجود فيه يظهر في فلتر التحليل.
    - البرنامج المحذوف منه يختفي من الفلتر.
    - تبقى السجلات التاريخية داخل AcademicProgram دون حذف فعلي.
    """
    master_keys = _sync_master_program_catalog()

    programs = list(
        AcademicProgram.objects.all()
    )

    evaluation_counts = (
        _evaluation_file_counts_by_program()
    )

    canonical_by_key = {}

    for program in programs:
        key = _program_identity_key(program)

        if not any(key):
            key = (
                "program-id",
                str(program.id),
            )

        normalized_display_key = _normalize_program_text(
            _program_display_name(program)
        )

        # إذا كان جدول البرامج الرئيسي متاحًا،
        # فلا نعرض إلا البرامج الموجودة فيه حاليًا.
        if (
            master_keys is not None
            and normalized_display_key not in master_keys
        ):
            continue

        # لا نعرض السجلات غير النشطة.
        if not bool(
            getattr(program, "is_active", True)
        ):
            continue

        current = canonical_by_key.get(key)

        if (
            current is None
            or _program_preference_key(
                program,
                evaluation_counts,
            )
            < _program_preference_key(
                current,
                evaluation_counts,
            )
        ):
            canonical_by_key[key] = program

    canonical_programs = list(
        canonical_by_key.values()
    )

    canonical_programs.sort(
        key=lambda program: (
            _normalize_program_text(
                _program_display_name(program)
            ),
            int(program.id),
        )
    )

    id_to_canonical = {}

    # بناء خريطة كل السجلات، بما فيها غير النشطة،
    # حتى تظل ملفات التقييم التاريخية قابلة للقراءة.
    all_canonical_by_key = {}

    for program in programs:
        key = _program_identity_key(program)

        if not any(key):
            key = (
                "program-id",
                str(program.id),
            )

        current = all_canonical_by_key.get(key)

        if (
            current is None
            or _program_preference_key(
                program,
                evaluation_counts,
            )
            < _program_preference_key(
                current,
                evaluation_counts,
            )
        ):
            all_canonical_by_key[key] = program

    for program in programs:
        key = _program_identity_key(program)

        if not any(key):
            key = (
                "program-id",
                str(program.id),
            )

        canonical_program = all_canonical_by_key.get(
            key
        )

        id_to_canonical[program.id] = (
            canonical_program.id
            if canonical_program
            else program.id
        )

    return canonical_programs, id_to_canonical

def _canonical_program_id(
    program_id,
    id_to_canonical=None,
):
    """
    تحويل معرف أي سجل مكرر إلى معرف السجل الأساسي.
    """
    if not program_id or program_id == "all":
        return program_id

    try:
        numeric_program_id = int(program_id)
    except (TypeError, ValueError):
        return program_id

    if id_to_canonical is None:
        _, id_to_canonical = (
            _get_canonical_program_data()
        )

    return str(
        id_to_canonical.get(
            numeric_program_id,
            numeric_program_id,
        )
    )


def _equivalent_program_ids(program_id):
    """
    جميع المعرفات التي تمثل البرنامج نفسه، لاستخدامها عند
    قراءة ملفات التقييم المرتبطة بأي نسخة مكررة.
    """
    try:
        selected_program = AcademicProgram.objects.get(
            id=program_id
        )
    except (
        AcademicProgram.DoesNotExist,
        TypeError,
        ValueError,
    ):
        return [program_id]

    selected_key = _program_identity_key(
        selected_program
    )

    equivalent_ids = [
        program.id
        for program in AcademicProgram.objects.all()
        if _program_identity_key(program) == selected_key
    ]

    return equivalent_ids or [
        selected_program.id
    ]


def _get_program_options():
    """
    عرض جميع البرامج الأكاديمية النشطة دون تكرار،
    حتى لو لم يتم إنشاء ملف تقييم لها بعد.
    """
    canonical_programs, _ = (
        _get_canonical_program_data()
    )

    return canonical_programs


def _get_program_years_map(
    id_to_canonical=None,
):
    """
    سنوات التقييم لكل برنامج بعد دمج السجلات المتكررة.
    """
    if id_to_canonical is None:
        _, id_to_canonical = (
            _get_canonical_program_data()
        )

    rows = (
        EvaluationFile.objects
        .exclude(status="template_preview")
        .exclude(academic_year="")
        .values(
            "program_id",
            "academic_year",
        )
        .distinct()
    )

    result = {}

    for row in rows:
        program_id = row.get("program_id")

        academic_year = str(
            row.get("academic_year") or ""
        ).strip()

        if not program_id or not academic_year:
            continue

        canonical_id = id_to_canonical.get(
            program_id,
            program_id,
        )

        key = str(canonical_id)

        result.setdefault(
            key,
            set(),
        ).add(academic_year)

    sorted_result = {}

    for program_id, years in result.items():
        sorted_result[program_id] = sorted(
            years,
            key=_extract_year_start,
            reverse=True,
        )

    return sorted_result


def _available_years_for_program(program_years_map, program_id, all_years):
    if not program_id or program_id == "all":
        return list(all_years)

    return list(program_years_map.get(str(program_id), []))


def _build_calculation_explanation(
    summary,
    is_aggregate_analysis=False,
    is_all_programs=False,
    is_all_years=False,
):
    """نصوص شرح مبسطة تظهر داخل صفحة التحليل، حتى يفهم المستخدم مصدر كل رقم."""
    if not summary:
        return []

    if is_aggregate_analysis:
        if is_all_programs and is_all_years:
            scope_text = (
                "النظام جمع كل ملفات التقييم المحفوظة لكل البرامج وفي كل السنوات، "
                "ثم حسب المتوسطات. لذلك الأرقام هنا تمثل صورة عامة للنظام كاملًا، وليست حكمًا على برنامج واحد."
            )
        elif is_all_programs:
            scope_text = (
                "النظام أخذ ملفات التقييم الموجودة في السنة المختارة لكل البرامج، "
                "ثم حسب متوسط كل معيار بين هذه البرامج."
            )
        elif is_all_years:
            scope_text = (
                "النظام أخذ كل سنوات البرنامج المختار، ثم حسب متوسط الأداء عبر السنوات المحفوظة لهذا البرنامج."
            )
        else:
            scope_text = (
                "النظام حسب متوسط الملفات الداخلة في النطاق الذي حددته من الفلاتر."
            )
    else:
        scope_text = (
            "النظام يستخدم ملف تقييم واحد فقط: البرنامج والسنة المختارين من الفلاتر. "
            "كل الأرقام المعروضة تخص هذا الملف فقط."
        )

    return [
        {
            "title": "مصدر البيانات",
            "text": scope_text,
        },
        {
            "title": "نسبة كل معيار",
            "text": (
                "كل معيار له درجة من 5. النسبة المعروضة للمعيار تحسب هكذا: "
                "درجة المعيار ÷ 5 × 100. مثال: درجة 4 من 5 = 80%."
            ),
        },
        {
            "title": "النتيجة العامة",
            "text": (
                "النتيجة العامة لا تجمع نسب المعايير مباشرة. كل معيار له وزن مختلف، "
                "لذلك يحسب النظام مساهمة كل معيار حسب وزنه ثم يجمع المساهمات للوصول إلى النسبة النهائية."
            ),
        },
        {
            "title": "أي درجة يستخدمها النظام؟",
            "text": (
                "إذا كانت درجة المراجع موجودة فيستخدمها النظام لأنها الدرجة المعتمدة للمراجعة. "
                "إذا لم توجد درجة مراجع، يستخدم النظام درجة التقييم الآلي حتى لا يبقى التحليل فارغًا."
            ),
        },
        {
            "title": "معنى مستوى الأداء",
            "text": (
                "أقل من 50% = منخفض ويحتاج معالجة. من 50% إلى أقل من 80% = يحتاج تحسين. "
                "80% فأعلى = جيد. هذه الحدود تساعد المستخدم على فهم اللون والحالة بسرعة."
            ),
        },
    ]

def _get_latest_review():
    return (
        ProgramEvaluationReview.objects
        .select_related("evaluation_file", "evaluation_file__program")
        .exclude(evaluation_file__status="template_preview")
        .order_by("-updated_at")
        .first()
    )


def _get_review_for_file(selected_file):
    if not selected_file:
        return None

    return (
        ProgramEvaluationReview.objects
        .select_related("evaluation_file", "evaluation_file__program")
        .filter(evaluation_file=selected_file)
        .first()
    )


def _get_file_for_program_and_year(program_id, academic_year):
    if not program_id or not academic_year or academic_year == "all":
        return None

    return (
        EvaluationFile.objects
        .select_related("program")
        .exclude(status="template_preview")
        .filter(
            program_id__in=_equivalent_program_ids(
                program_id
            ),
            academic_year=academic_year,
        )
        .order_by("-updated_at")
        .first()
    )


def _get_reviews_for_scope(academic_year="all", program_id="all", user=None):
    evaluation_files = (
        EvaluationFile.objects
        .select_related("program")
        .exclude(status="template_preview")
        .order_by(
            "program__name",
            "program__specialization",
            "academic_year",
            "-updated_at",
        )
    )

    if academic_year and academic_year != "all":
        evaluation_files = evaluation_files.filter(academic_year=academic_year)

    if program_id and program_id != "all":
        evaluation_files = evaluation_files.filter(
            program_id__in=_equivalent_program_ids(
                program_id
            )
        )

    result = []
    seen_keys = set()

    for evaluation_file in evaluation_files:
        key = (
            _program_identity_key(
                evaluation_file.program
            ),
            evaluation_file.academic_year,
        )

        if key in seen_keys:
            continue

        seen_keys.add(key)

        review = (
            ProgramEvaluationReview.objects
            .select_related("evaluation_file", "evaluation_file__program")
            .filter(evaluation_file=evaluation_file)
            .first()
        )

        if not review:
            review = generate_auto_review(
                evaluation_file,
                user,
            )

        result.append(review)

    return result


def _get_reviews_for_year(academic_year, user=None):
    return _get_reviews_for_scope(
        academic_year=academic_year,
        program_id="all",
        user=user,
    )


def _get_previous_academic_year(current_year, academic_year_options):
    if not current_year or current_year == "all":
        return ""

    current_start = _extract_year_start(current_year)

    older_years = [
        year for year in academic_year_options
        if _extract_year_start(year) < current_start
    ]

    if not older_years:
        return ""

    older_years.sort(
        key=lambda value: _extract_year_start(value),
        reverse=True,
    )

    return older_years[0]


# ============================================================
# قراءة جودة المؤشرات
# ============================================================

def _count_indicator_quality(standard_review):
    strong_count = 0
    weak_count = 0

    # نستخدم set حتى لا يتكرر الحقل الناقص نفسه
    unique_missing_items = set()

    for indicator in standard_review.indicator_reviews.all():
        final_score = (
            indicator.reviewer_score
            if indicator.reviewer_score is not None
            else indicator.auto_score
        )

        if int(final_score or 1) >= 4:
            strong_count += 1

        if int(final_score or 1) <= 2:
            weak_count += 1

        snapshot = indicator.data_snapshot or {}

        # استبعاد المؤشرات التوثيقية المرتبطة بالمرفقات فقط
        if not snapshot.get("included_in_standard", True):
            continue

        missing_items = snapshot.get("missing_items", [])

        if not isinstance(missing_items, list):
            continue

        for item in missing_items:
            normalized_item = str(item or "").strip()

            if normalized_item:
                unique_missing_items.add(normalized_item)

    missing_items_list = sorted(unique_missing_items)

    return (
        strong_count,
        weak_count,
        len(missing_items_list),
        missing_items_list,
    )


# ============================================================
# بناء صفوف المعايير لبرنامج واحد
# ============================================================

def _build_standard_rows(review, selected_status="all"):
    rows = []

    existing_plan_map = {
        plan.standard_review_id: plan.id
        for plan in ImprovementPlan.objects.filter(
            evaluation_file=review.evaluation_file,
            standard_review__isnull=False,
        ).only("id", "standard_review_id")
    }

    standard_reviews = (
        review.standard_reviews
        .select_related(
            "standard",
            "saved_by",
            "reviewed_by",
            "review__evaluation_file",
        )
        .prefetch_related("indicator_reviews")
        .order_by("standard__number")
    )

    if selected_status != "all":
        standard_reviews = standard_reviews.filter(review_status=selected_status)

    for standard_review in standard_reviews:
        final_percentage = _get_final_percentage(standard_review)
        final_score = _get_final_score(standard_review)
        risk = _risk_info(final_percentage, standard_review.review_status)

        (
    strong_count,
    weak_count,
    missing_items_count,
    missing_items_list,
) = _count_indicator_quality(
    standard_review
)

        indicators_count = standard_review.indicator_reviews.count()

        evaluation_url = (
            f"{reverse('evaluation')}"
            f"?file_id={standard_review.review.evaluation_file.id}"
            f"&standard_review_id={standard_review.id}"
            f"&load_draft=1"
            f"#standard-{standard_review.standard.number}"
        )

        improvement_plan_id = existing_plan_map.get(standard_review.id)

        improvement_plan_url = ""
        if improvement_plan_id:
            improvement_plan_url = (
                f"{reverse('improvement_plans')}"
                f"?file_id={standard_review.review.evaluation_file.id}"
                f"&open_plan={improvement_plan_id}"
                f"#plan-{improvement_plan_id}"
            )

        should_show_improvement_action = (
            bool(improvement_plan_id)
            or standard_review.review_status != "reviewed"
            or _as_decimal(final_percentage) < Decimal("80")
            or bool(standard_review.weaknesses)
            or bool(standard_review.improvement_plan)
        )

        rows.append({
            "id": standard_review.id,
            "is_aggregate": False,

            "program_name": _program_name(standard_review.review),
            "academic_year": _academic_year(standard_review.review),

            "evaluation_url": evaluation_url,

            "standard_number": standard_review.standard.number,
            "standard_title": standard_review.standard.title,
            "weight": standard_review.weight,

            "review_status": standard_review.review_status,
            "status_label": _status_label(standard_review.review_status),
            "status_class": _status_class(standard_review.review_status),

            "auto_percentage": standard_review.auto_percentage,
            "reviewer_percentage": standard_review.reviewer_percentage,
            "final_percentage": final_percentage,
            "final_percentage_float": _as_float(final_percentage),
            "bar_width": _css_width_value(final_percentage),

            "final_score": final_score,
            "final_score_float": _as_float(final_score),
            "final_score_label": score_label(final_score),
            "quality_label": _quality_label(final_percentage),

            "risk_label": risk["label"],
            "risk_class": risk["class"],
            "risk_note": risk["note"],
            "performance_class": _performance_class_by_percentage(final_percentage),

            "indicators_count": indicators_count,
            "strong_count": strong_count,
            "weak_count": weak_count,
            "missing_items_count": missing_items_count,

            "programs_count": 1,
            "weak_programs_count": 1 if risk["class"] == "risk-high" else 0,
            "needs_improvement_programs_count": 1 if risk["class"] in ["risk-high", "risk-medium"] else 0,

            "strengths": standard_review.strengths,
            "weaknesses": standard_review.weaknesses,
            "improvement_plan": standard_review.improvement_plan,
            "execution_time": standard_review.execution_time,

            "has_improvement_plan": bool(improvement_plan_id),
            "improvement_plan_id": improvement_plan_id,
            "improvement_plan_url": improvement_plan_url,
            "should_show_improvement_action": should_show_improvement_action,
            "missing_items_count": missing_items_count,
            "missing_items_list": missing_items_list,
        })

    return rows


# ============================================================
# بناء صفوف المعايير عند التحليل الجماعي
# ============================================================

def _build_aggregate_standard_rows(reviews, selected_status="all"):
    grouped = {}

    for review in reviews:
        rows = _build_standard_rows(review, selected_status=selected_status)

        for row in rows:
            key = row["standard_number"]

            if key not in grouped:
                grouped[key] = {
                    "standard_number": row["standard_number"],
                    "standard_title": row["standard_title"],
                    "weight": row["weight"],

                    "percentages": [],
                    "scores": [],

                    "indicators_count": 0,
                    "strong_count": 0,
                    "weak_count": 0,
                    "missing_items_count": 0,

                    "programs_count": 0,
                    "weak_programs_count": 0,
                    "needs_improvement_programs_count": 0,
                }

            item = grouped[key]

            item["percentages"].append(_as_decimal(row["final_percentage"]))
            item["scores"].append(_as_decimal(row["final_score"]))

            item["indicators_count"] += int(row["indicators_count"] or 0)
            item["strong_count"] += int(row["strong_count"] or 0)
            item["weak_count"] += int(row["weak_count"] or 0)
            item["missing_items_count"] += int(row["missing_items_count"] or 0)

            item["programs_count"] += 1

            if row["risk_class"] == "risk-high":
                item["weak_programs_count"] += 1

            if row["risk_class"] in ["risk-high", "risk-medium"]:
                item["needs_improvement_programs_count"] += 1

    aggregate_rows = []

    for key in sorted(grouped.keys()):
        item = grouped[key]

        if item["percentages"]:
            average_percentage = sum(item["percentages"]) / Decimal(len(item["percentages"]))
        else:
            average_percentage = Decimal("0")

        if item["scores"]:
            average_score = sum(item["scores"]) / Decimal(len(item["scores"]))
        else:
            average_score = Decimal("0")

        average_percentage = _round_decimal(average_percentage)
        average_score = _round_decimal(average_score)

        risk = _risk_info(average_percentage)

        aggregate_rows.append({
            "id": f"aggregate-{item['standard_number']}",
            "is_aggregate": True,

            "program_name": "متوسط النطاق",
            "academic_year": "",

            "evaluation_url": "#",

            "standard_number": item["standard_number"],
            "standard_title": item["standard_title"],
            "weight": item["weight"],

            "review_status": "aggregate",
            "status_label": f"متوسط {item['programs_count']} ملف",
            "status_class": "is-draft",

            "auto_percentage": average_percentage,
            "reviewer_percentage": None,
            "final_percentage": average_percentage,
            "final_percentage_float": _as_float(average_percentage),
            "bar_width": _css_width_value(average_percentage),

            "final_score": average_score,
            "final_score_float": _as_float(average_score),
            "final_score_label": f"{average_score} / 5",
            "quality_label": _quality_label(average_percentage),

            "risk_label": risk["label"],
            "risk_class": risk["class"],
            "risk_note": (
                f"هذا المتوسط محسوب من {item['programs_count']} ملف تقييم ضمن النطاق المحدد."
            ),
            "performance_class": _performance_class_by_percentage(average_percentage),

            "indicators_count": item["indicators_count"],
            "strong_count": item["strong_count"],
            "weak_count": item["weak_count"],
            "missing_items_count": item["missing_items_count"],

            "programs_count": item["programs_count"],
            "weak_programs_count": item["weak_programs_count"],
            "needs_improvement_programs_count": item["needs_improvement_programs_count"],

            "strengths": "",
            "weaknesses": "",
            "improvement_plan": "",
            "execution_time": "",

            "has_improvement_plan": False,
            "improvement_plan_id": None,
            "improvement_plan_url": "",
            "should_show_improvement_action": False,
        })

    return aggregate_rows


# ============================================================
# الملخص العام
# ============================================================

def _build_summary_from_review(review, rows):
    total = review.standard_reviews.count()

    reviewed_count = review.standard_reviews.filter(review_status="reviewed").count()
    draft_count = review.standard_reviews.filter(review_status="draft").count()
    needs_review_count = review.standard_reviews.filter(review_status="empty").count()

    return _build_summary_base(
        rows=rows,
        total_standards=total,
        reviewed_count=reviewed_count,
        draft_count=draft_count,
        needs_review_count=needs_review_count,
        final_percentage=review.final_percentage or 0,
        auto_percentage=review.overall_auto_percentage or 0,
        reviewer_percentage=review.overall_reviewer_percentage,
        total_standard_instances=total,
        total_programs=1,
        total_reviews=1,
        total_years=1,
    )


def _build_summary_from_reviews(reviews, rows):
    total_standards = 0
    reviewed_count = 0
    draft_count = 0
    needs_review_count = 0

    review_percentages = []
    program_keys = set()
    academic_years = set()

    for review in reviews:
        total_standards += review.standard_reviews.count()

        reviewed_count += review.standard_reviews.filter(
            review_status="reviewed"
        ).count()

        draft_count += review.standard_reviews.filter(
            review_status="draft"
        ).count()

        needs_review_count += review.standard_reviews.filter(
            review_status="empty"
        ).count()

        review_percentages.append(
            _as_decimal(review.final_percentage or 0)
        )

        evaluation_file = getattr(review, "evaluation_file", None)

        if evaluation_file:
            program = getattr(evaluation_file, "program", None)

            if program:
                # العد يعتمد على الاسم والتخصص بعد توحيد
                # اختلافات الهمزات، مثل إلكترونية / الكترونية.
                program_key = _program_identity_key(
                    program
                )

                if any(program_key):
                    program_keys.add(program_key)

            elif evaluation_file.program_id:
                # مسار احتياطي عند غياب بيانات البرنامج.
                program_keys.add(
                    ("program-id", str(evaluation_file.program_id))
                )

            academic_year = str(
                evaluation_file.academic_year or ""
            ).strip()

            if academic_year:
                academic_years.add(academic_year)

    if review_percentages:
        final_percentage = (
            sum(review_percentages)
            / Decimal(len(review_percentages))
        )
    else:
        final_percentage = Decimal("0")

    return _build_summary_base(
        rows=rows,
        total_standards=len(rows),
        reviewed_count=reviewed_count,
        draft_count=draft_count,
        needs_review_count=needs_review_count,
        final_percentage=_round_decimal(final_percentage),
        auto_percentage=_round_decimal(final_percentage),
        reviewer_percentage=None,
        total_standard_instances=total_standards,
        total_programs=len(program_keys),
        total_reviews=len(reviews),
        total_years=len(academic_years),
    )

def _build_summary_base(
    rows,
    total_standards,
    reviewed_count,
    draft_count,
    needs_review_count,
    final_percentage,
    auto_percentage,
    reviewer_percentage,
    total_standard_instances=None,
    total_programs=1,
    total_reviews=1,
    total_years=1,
):
    total_status_items = reviewed_count + draft_count + needs_review_count

    high_risk_count = len([
        row for row in rows
        if row["risk_class"] == "risk-high"
    ])

    medium_risk_count = len([
        row for row in rows
        if row["risk_class"] == "risk-medium"
    ])

    low_risk_count = len([
        row for row in rows
        if row["risk_class"] == "risk-low"
    ])

    average_score = Decimal("0")
    if rows:
        average_score = sum(
            _as_decimal(row["final_score"])
            for row in rows
        ) / Decimal(len(rows))

    weakest_row = None
    strongest_row = None

    if rows:
        weakest_row = min(rows, key=lambda item: item["final_percentage_float"])
        strongest_row = max(rows, key=lambda item: item["final_percentage_float"])

    return {
        "total_standards": total_standards,
        "total_standard_instances": total_standard_instances or total_status_items,
        "total_programs": total_programs,
        "total_reviews": total_reviews,
        "total_years": total_years,

        "reviewed_count": reviewed_count,
        "draft_count": draft_count,
        "needs_review_count": needs_review_count,

        "reviewed_percentage": _percentage(reviewed_count, total_status_items),
        "draft_percentage": _percentage(draft_count, total_status_items),
        "needs_review_percentage": _percentage(needs_review_count, total_status_items),

        "final_percentage": _round_decimal(final_percentage),
        "final_percentage_float": _as_float(final_percentage),
        "auto_percentage": _round_decimal(auto_percentage),
        "reviewer_percentage": reviewer_percentage,

        "average_score": _round_decimal(average_score),
        "average_score_float": _as_float(average_score),

        "final_status_label": _quality_label(final_percentage),
        "quality_label": _quality_label(final_percentage),

        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "low_risk_count": low_risk_count,

        "weakest_row": weakest_row,
        "strongest_row": strongest_row,
    }


# ============================================================
# مؤشر حالة الاعتماد
# ============================================================

def _build_approval_indicator(summary, can_issue_official, is_aggregate_analysis=False):
    final_percentage = _as_decimal(summary.get("final_percentage", 0))
    blockers = summary.get("draft_count", 0) + summary.get("needs_review_count", 0)

    if is_aggregate_analysis:
        if blockers > 0:
            return {
                "label": "متوسط النطاق غير جاهز للحكم النهائي",
                "class": "is-warning",
                "percentage": final_percentage,
                "note": (
                    f"تم تحليل {summary.get('total_reviews', 0)} ملف تقييم ضمن النطاق المحدد، "
                    f"لكن توجد {blockers} حالة معيار لم تعتمد بعد."
                ),
            }

        if final_percentage >= 80:
            return {
                "label": "المستوى العام جيد",
                "class": "is-complete",
                "percentage": final_percentage,
                "note": "متوسط الأداء في النطاق المحدد جيد وقابل للاعتماد كمؤشر عام.",
            }

        return {
            "label": "يحتاج تحسين على مستوى النطاق",
            "class": "is-warning",
            "percentage": final_percentage,
            "note": "متوسط الأداء العام أقل من المستوى المطلوب ويحتاج معالجة على مستوى البرامج أو السنوات.",
        }

    if can_issue_official and final_percentage >= 80:
        return {
            "label": "جاهز للاعتماد",
            "class": "is-complete",
            "percentage": final_percentage,
            "note": "جميع المعايير معتمدة والنتيجة النهائية مناسبة للاعتماد.",
        }

    if blockers > 0:
        return {
            "label": "غير مكتمل",
            "class": "is-warning",
            "percentage": final_percentage,
            "note": f"يوجد {blockers} معيار لم يعتمد بعد، لذلك لا يمكن إصدار حكم نهائي.",
        }

    if final_percentage >= 65:
        return {
            "label": "يحتاج متابعة وتحسين",
            "class": "is-warning",
            "percentage": final_percentage,
            "note": "البرنامج مقبول مبدئيًا، لكنه يحتاج خطة تحسين للمعايير الأقل أداءً.",
        }

    return {
        "label": "يحتاج معالجة عاجلة",
        "class": "is-blocked",
        "percentage": final_percentage,
        "note": "النتيجة الحالية منخفضة وتحتاج معالجة واضحة قبل الاعتماد.",
    }


# ============================================================
# التوصيات والقراءة
# ============================================================

def _build_recommendations(rows, summary, is_aggregate_analysis=False):
    recommendations = []

    high_risk_rows = [
        row for row in rows
        if row["risk_class"] == "risk-high"
    ]

    weak_rows = sorted(
        rows,
        key=lambda item: item["final_percentage_float"]
    )[:3]

    if not rows:
        return [
            "لا توجد معايير متاحة للتحليل. يجب توليد التقييم أولًا من صفحة التقييم."
        ]

    if summary["needs_review_count"]:
        recommendations.append(
            f"يوجد {summary['needs_review_count']} معيار بحاجة إلى مراجعة؛ يجب استكمال مراجعته قبل إصدار حكم نهائي."
        )

    if summary["draft_count"]:
        recommendations.append(
            f"يوجد {summary['draft_count']} معيار محفوظ كمسودة؛ يجب مراجعته واعتماده قبل إصدار الحكم النهائي."
        )

    if high_risk_rows:
        recommendations.append(
            f"يوجد {len(high_risk_rows)} معيار بدرجة خطورة مرتفعة؛ يوصى بإعطائها أولوية في خطة التحسين."
        )

    if weak_rows:
        weakest = weak_rows[0]

        if is_aggregate_analysis:
            recommendations.append(
                f"أضعف معيار ضمن النطاق المحدد هو: {weakest['standard_title']} بمتوسط {weakest['final_percentage']}%."
            )
        else:
            recommendations.append(
                f"أضعف معيار حاليًا هو: {weakest['standard_title']} بنسبة {weakest['final_percentage']}%."
            )

    if is_aggregate_analysis:
        repeated_weak = [
            row for row in rows
            if row.get("weak_programs_count", 0) > 1
        ]

        if repeated_weak:
            top_repeated = sorted(
                repeated_weak,
                key=lambda item: item["weak_programs_count"],
                reverse=True,
            )[0]

            recommendations.append(
                f"المعيار الأكثر تكرارًا كضعف هو: {top_repeated['standard_title']}، "
                f"وظهر ضعفه في {top_repeated['weak_programs_count']} ملف تقييم."
            )

    if _as_decimal(summary["final_percentage"]) >= 80 and not high_risk_rows:
        recommendations.append(
            "الوضع العام جيد، لكن يفضل الاستمرار في توثيق الأدلة وتحويل المسودات إلى اعتماد نهائي."
        )

    if not recommendations:
        recommendations.append(
            "لا توجد فجوات جوهرية ظاهرة حاليًا، مع ضرورة مراجعة الأدلة قبل الاعتماد النهائي."
        )

    return recommendations


def _build_analysis_reading(rows, summary, priority_rows, is_aggregate_analysis=False):
    if not rows:
        return {
            "main_text": "لا توجد بيانات كافية لبناء قراءة تحليلية.",
            "strong_text": "",
            "weak_text": "",
            "conclusion_text": "",
        }

    strongest = summary.get("strongest_row")
    weakest = summary.get("weakest_row")

    if is_aggregate_analysis:
        main_text = (
            f"تم تحليل {summary['total_reviews']} ملف تقييم ضمن النطاق المحدد. "
            f"المؤشر العام هو {summary['final_percentage']}% "
            f"ومتوسط درجة التوفر هو {summary['average_score']} من 5."
        )
    else:
        main_text = (
            f"تم تحليل {summary['total_standards']} معيار. "
            f"النسبة النهائية الحالية هي {summary['final_percentage']}% "
            f"ومتوسط درجة التوفر هو {summary['average_score']} من 5."
        )

    strong_text = ""
    if strongest:
        strong_text = (
            f"أقوى معيار هو {strongest['standard_title']} "
            f"بنسبة {strongest['final_percentage']}%."
        )

    weak_text = ""
    if weakest:
        weak_text = (
            f"أضعف معيار هو {weakest['standard_title']} "
            f"بنسبة {weakest['final_percentage']}%."
        )

    conclusion_text = "لا توجد أولوية تحسين واضحة حاليًا."

    if priority_rows:
        priority = priority_rows[0]
        conclusion_text = (
            f"ينصح بالبدء في تحسين معيار {priority['standard_title']} "
            f"لأنه أعلى معيار في أولوية التحسين الحالية."
        )

    return {
        "main_text": main_text,
        "strong_text": strong_text,
        "weak_text": weak_text,
        "conclusion_text": conclusion_text,
    }


# ============================================================
# الرؤى السريعة
# ============================================================

def _build_insights(rows, summary, selected_analysis_mode, can_issue_official, is_aggregate_analysis=False):
    if not rows:
        return {
            "readiness_label": "لا توجد بيانات",
            "readiness_class": "is-warning",
            "readiness_note": "لا توجد معايير كافية لبناء قراءة تحليلية.",
            "strongest_row": None,
            "weakest_row": None,
            "priority_row": None,
        }

    strongest_row = max(
        rows,
        key=lambda item: item["final_percentage_float"]
    )

    weakest_row = min(
        rows,
        key=lambda item: item["final_percentage_float"]
    )

    priority_candidates = sorted(
        rows,
        key=lambda item: (
            0 if item["risk_class"] == "risk-high" else 1,
            item["final_percentage_float"],
            -item["missing_items_count"],
        )
    )

    priority_row = priority_candidates[0] if priority_candidates else None

    if is_aggregate_analysis:
        readiness_label = "متوسط النطاق"
        readiness_class = "is-warning"
        readiness_note = "هذا التحليل يعرض متوسط الأداء ضمن النطاق المحدد."
    elif selected_analysis_mode == "official" and not can_issue_official:
        readiness_label = "غير جاهز رسميًا"
        readiness_class = "is-blocked"
        readiness_note = "لا يمكن اعتماد التحليل رسميًا قبل اعتماد جميع المعايير."
    elif summary["draft_count"] or summary["needs_review_count"]:
        readiness_label = "جاهز للمتابعة"
        readiness_class = "is-warning"
        readiness_note = "التحليل مناسب للمتابعة الداخلية، لكنه ليس حكمًا نهائيًا بعد."
    else:
        readiness_label = "جاهز للاعتماد"
        readiness_class = "is-complete"
        readiness_note = "جميع المعايير معتمدة ويمكن الاعتماد على النتيجة الحالية."

    return {
        "readiness_label": readiness_label,
        "readiness_class": readiness_class,
        "readiness_note": readiness_note,
        "strongest_row": strongest_row,
        "weakest_row": weakest_row,
        "priority_row": priority_row,
    }


# ============================================================
# أداء المعايير
# ============================================================

def _build_performance_bars(rows):
    performance_rows = sorted(
        rows,
        key=lambda item: item["standard_number"]
    )

    return [
        {
            "standard_number": row["standard_number"],
            "standard_title": row["standard_title"],
            "final_percentage": row["final_percentage"],
            "final_percentage_float": row["final_percentage_float"],
            "bar_width": row.get("bar_width", _css_width_value(row["final_percentage"])),
            "quality_label": row["quality_label"],
            "risk_class": row["risk_class"],
            "risk_label": row["risk_label"],
            "performance_class": _performance_class_by_percentage(row["final_percentage"]),
            "evaluation_url": row["evaluation_url"],
            "is_aggregate": row.get("is_aggregate", False),
            "programs_count": row.get("programs_count", 1),
            "weak_programs_count": row.get("weak_programs_count", 0),
        }
        for row in performance_rows
    ]


# ============================================================
# أولويات التحسين
# ============================================================

def _priority_label(priority_value):
    value = _as_decimal(priority_value)

    if value >= 10:
        return "أولوية مرتفعة"

    if value >= 5:
        return "أولوية متوسطة"

    return "أولوية منخفضة"


def _build_smart_priorities(rows):
    priority_rows = []

    for row in rows:
        final_percentage = _as_decimal(row["final_percentage"])
        weight = _as_decimal(row["weight"])

        gap = Decimal("80") - final_percentage
        if gap < 0:
            gap = Decimal("0")

        if row["review_status"] == "empty":
            gap += Decimal("20")

        if row["risk_class"] == "risk-high":
            gap += Decimal("10")

        if row.get("is_aggregate") and row.get("weak_programs_count", 0):
            gap += Decimal(row["weak_programs_count"])

        priority_value = _round_decimal((gap * weight) / Decimal("10"))

        needs_priority = (
            priority_value > 0
            or row["risk_class"] in ["risk-high", "risk-medium"]
            or row["review_status"] != "reviewed"
        )

        if not needs_priority:
            continue

        priority_rows.append({
            **row,
            "priority_value": priority_value,
            "priority_value_float": _as_float(priority_value),
            "priority_label": _priority_label(priority_value),
        })

    priority_rows.sort(
        key=lambda item: (
            -item["priority_value_float"],
            item["final_percentage_float"],
            -item["missing_items_count"],
        )
    )

    return priority_rows[:4]


# ============================================================
# المقارنة الزمنية
# ============================================================

def _find_previous_review(review, academic_year_options):
    if not review or not review.evaluation_file:
        return None

    previous_year = _get_previous_academic_year(
        review.evaluation_file.academic_year,
        academic_year_options,
    )

    if not previous_year:
        return None

    return (
        ProgramEvaluationReview.objects
        .select_related("evaluation_file", "evaluation_file__program")
        .filter(
            evaluation_file__program=review.evaluation_file.program,
            evaluation_file__academic_year=previous_year,
        )
        .exclude(id=review.id)
        .order_by("-updated_at")
        .first()
    )


def _build_temporal_comparison_for_review(review, current_rows, current_summary, academic_year_options):
    previous_review = _find_previous_review(review, academic_year_options)

    if not previous_review:
        return {
            "has_previous": False,
            "current_year": _academic_year(review),
            "previous_year": "",
            "overall_difference": None,
            "overall_trend_label": "لا توجد مقارنة سابقة",
            "overall_trend_class": "is-neutral",
            "rows": [],
            "message": "لا توجد بيانات لعام سابق لنفس البرنامج حتى الآن.",
        }

    previous_rows = _build_standard_rows(previous_review, selected_status="all")
    previous_summary = _build_summary_from_review(previous_review, previous_rows)

    return _build_temporal_comparison_base(
        current_year=_academic_year(review),
        previous_year=_academic_year(previous_review),
        current_rows=current_rows,
        previous_rows=previous_rows,
        current_summary=current_summary,
        previous_summary=previous_summary,
    )


def _build_temporal_comparison_for_all_programs(
    current_year,
    current_rows,
    current_summary,
    academic_year_options,
    user=None,
):
    previous_year = _get_previous_academic_year(current_year, academic_year_options)

    if not previous_year:
        return {
            "has_previous": False,
            "current_year": current_year,
            "previous_year": "",
            "overall_difference": None,
            "overall_trend_label": "لا توجد مقارنة سابقة",
            "overall_trend_class": "is-neutral",
            "rows": [],
            "message": "لا توجد بيانات لعام سابق للمقارنة الجماعية.",
        }

    previous_reviews = _get_reviews_for_year(previous_year, user=user)

    if not previous_reviews:
        return {
            "has_previous": False,
            "current_year": current_year,
            "previous_year": previous_year,
            "overall_difference": None,
            "overall_trend_label": "لا توجد مقارنة سابقة",
            "overall_trend_class": "is-neutral",
            "rows": [],
            "message": "توجد سنة سابقة، لكن لا توجد تقييمات مكتملة فيها.",
        }

    previous_rows = _build_aggregate_standard_rows(previous_reviews, selected_status="all")
    previous_summary = _build_summary_from_reviews(previous_reviews, previous_rows)

    return _build_temporal_comparison_base(
        current_year=current_year,
        previous_year=previous_year,
        current_rows=current_rows,
        previous_rows=previous_rows,
        current_summary=current_summary,
        previous_summary=previous_summary,
    )


def _build_temporal_comparison_base(
    current_year,
    previous_year,
    current_rows,
    previous_rows,
    current_summary,
    previous_summary,
):
    previous_map = {
        row["standard_number"]: row
        for row in previous_rows
    }

    comparison_rows = []

    for row in current_rows:
        previous_row = previous_map.get(row["standard_number"])

        if not previous_row:
            continue

        current_score = _as_decimal(row["final_score"])
        previous_score = _as_decimal(previous_row["final_score"])
        score_difference = _round_decimal(current_score - previous_score)

        if score_difference > 0:
            trend_label = "تحسن"
            trend_class = "is-up"
        elif score_difference < 0:
            trend_label = "تراجع"
            trend_class = "is-down"
        else:
            trend_label = "ثابت"
            trend_class = "is-neutral"

        comparison_rows.append({
            "standard_number": row["standard_number"],
            "standard_title": row["standard_title"],
            "current_score": _round_decimal(current_score),
            "previous_score": _round_decimal(previous_score),
            "score_difference": score_difference,
            "trend_label": trend_label,
            "trend_class": trend_class,
        })

    overall_difference = _round_decimal(
        _as_decimal(current_summary["final_percentage"])
        - _as_decimal(previous_summary["final_percentage"])
    )

    if overall_difference > 0:
        overall_trend_label = "تحسن"
        overall_trend_class = "is-up"
    elif overall_difference < 0:
        overall_trend_label = "تراجع"
        overall_trend_class = "is-down"
    else:
        overall_trend_label = "ثابت"
        overall_trend_class = "is-neutral"

    return {
        "has_previous": True,
        "current_year": current_year,
        "previous_year": previous_year,
        "overall_difference": overall_difference,
        "overall_trend_label": overall_trend_label,
        "overall_trend_class": overall_trend_class,
        "previous_final_percentage": previous_summary["final_percentage"],
        "current_final_percentage": current_summary["final_percentage"],
        "rows": comparison_rows,
        "message": "",
    }


# ============================================================
# المقارنة بين البرامج
# ============================================================

def _build_program_comparison_by_scope(academic_year="all", user=None):
    reviews = _get_reviews_for_scope(
        academic_year=academic_year,
        program_id="all",
        user=user,
    )

    grouped = {}

    for review in reviews:
        program_key = _program_identity_key(
            review.evaluation_file.program
        )

        if program_key not in grouped:
            grouped[program_key] = []

        grouped[program_key].append(review)

    rows = []
    weak_standard_frequency = {}

    for program_reviews in grouped.values():
        if not program_reviews:
            continue

        first_review = program_reviews[0]
        standard_rows = _build_aggregate_standard_rows(
            program_reviews,
            selected_status="all",
        )

        if not standard_rows:
            continue

        summary = _build_summary_from_reviews(
            program_reviews,
            standard_rows,
        )

        weak_rows = [
            row for row in standard_rows
            if row["risk_class"] in ["risk-high", "risk-medium"]
        ]

        strong_rows = [
            row for row in standard_rows
            if row["risk_class"] == "risk-low"
        ]

        weakest_row = min(
            standard_rows,
            key=lambda row: row["final_percentage_float"]
        )

        for weak_row in weak_rows:
            weak_standard_frequency[weak_row["standard_title"]] = (
                weak_standard_frequency.get(weak_row["standard_title"], 0) + 1
            )

        if summary["final_percentage_float"] >= 80:
            status_label = "جيد"
            status_class = "risk-low"
        elif summary["final_percentage_float"] >= 65:
            status_label = "متوسط"
            status_class = "risk-medium"
        else:
            status_label = "يحتاج تحسين"
            status_class = "risk-high"

        rows.append({
            "program_name": _program_name(first_review),
            "academic_year": academic_year if academic_year != "all" else "كل السنوات",
            "final_percentage": summary["final_percentage"],
            "final_percentage_float": summary["final_percentage_float"],
            "average_score": summary["average_score"],
            "weak_count": len(weak_rows),
            "strong_count": len(strong_rows),
            "weakest_standard": weakest_row["standard_title"],
            "weakest_standard_score": weakest_row["final_score"],
            "status_label": status_label,
            "status_class": status_class,
        })

    rows.sort(
        key=lambda row: row["final_percentage_float"],
        reverse=True
    )

    best_program = rows[0] if rows else None
    weakest_program = rows[-1] if rows else None

    common_weak_standard = ""
    common_weak_count = 0

    if weak_standard_frequency:
        common_weak_standard, common_weak_count = max(
            weak_standard_frequency.items(),
            key=lambda item: item[1]
        )

    return {
        "rows": rows,
        "best_program": best_program,
        "weakest_program": weakest_program,
        "common_weak_standard": common_weak_standard,
        "common_weak_count": common_weak_count,
    }


# ============================================================
# التحليل التفصيلي
# ============================================================

def _build_detailed_rows(rows, sort_mode="weakest"):
    sorted_rows = list(rows)

    if sort_mode == "strongest":
        sorted_rows.sort(
            key=lambda item: item["final_percentage_float"],
            reverse=True
        )
    elif sort_mode == "priority":
        sorted_rows.sort(
            key=lambda item: (
                0 if item["risk_class"] == "risk-high" else 1,
                item["final_percentage_float"],
                -item["missing_items_count"],
            )
        )
    else:
        sorted_rows.sort(
            key=lambda item: item["final_percentage_float"]
        )

    return sorted_rows


# ============================================================
# تحليل الطلبة والأداء الأكاديمي
# ============================================================

ARABIC_NUMBER_TRANSLATION = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)


def _student_number(value, default=None):
    text = str(value or "").strip()

    if not text:
        return default

    text = (
        text.translate(ARABIC_NUMBER_TRANSLATION)
        .replace("%", "")
        .replace("٪", "")
        .replace("،", "")
        .replace(",", ".")
        .strip()
    )

    try:
        return float(text)
    except (TypeError, ValueError):
        return default


def _student_int(value):
    number = _student_number(value, 0)
    return int(round(number or 0))


def _student_average(values):
    clean_values = [
        float(value)
        for value in values
        if value is not None
    ]

    if not clean_values:
        return None

    return sum(clean_values) / len(clean_values)


def _student_display(value, suffix="%", decimals=2):
    if value is None:
        return "غير مسجل"

    return f"{float(value):.{decimals}f}{suffix}"



def _parse_student_faculty_ratio(value):
    text = str(value or "").strip()

    if not text:
        return None

    text = (
        text.translate(ARABIC_NUMBER_TRANSLATION)
        .replace(" ", "")
        .replace("：", ":")
    )

    if ":" in text:
        first_text, second_text = text.split(":", 1)
        first = _student_number(first_text)
        second = _student_number(second_text)

        if first and second is not None:
            return float(second) / float(first)

    number = _student_number(text)

    if number is None:
        return None

    return float(number)


def _student_faculty_ratio_display(value):
    if value is None:
        return "غير مسجل"

    rounded_value = round(float(value), 2)

    if rounded_value.is_integer():
        return f"1:{int(rounded_value)}"

    return f"1:{rounded_value:.2f}"

def _get_standard_form_data(evaluation_file, standard_number):
    if not evaluation_file:
        return {}

    entry = (
        StandardEntry.objects
        .filter(
            evaluation_file=evaluation_file,
            standard__number=standard_number,
        )
        .only("form_data")
        .first()
    )

    if not entry or not isinstance(entry.form_data, dict):
        return {}

    return entry.form_data


def _get_rate_value(form_data, average_key, male_key, female_key, *fallback_keys):
    average_value = _student_number(form_data.get(average_key))

    if average_value is not None:
        return average_value

    gender_average = _student_average([
        _student_number(form_data.get(male_key)),
        _student_number(form_data.get(female_key)),
    ])

    if gender_average is not None:
        return gender_average

    for key in fallback_keys:
        fallback_value = _student_number(form_data.get(key))

        if fallback_value is not None:
            return fallback_value

    return None


def _student_rate_class(metric_key, value):
    if value is None:
        return "is-empty"

    value = float(value)

    if metric_key == "cumulative_gpa":
        return "is-neutral"

    if metric_key == "withdrawal":
        if value <= 5:
            return "is-good"
        if value <= 10:
            return "is-warning"
        return "is-danger"

    if value >= 80:
        return "is-good"
    if value >= 60:
        return "is-warning"
    return "is-danger"


def _student_rate_note(metric_key, value):
    if value is None:
        return "لم يتم إدخال هذه النسبة."

    class_name = _student_rate_class(metric_key, value)

    notes = {
        "success": {
            "is-good": "معدل نجاح جيد.",
            "is-warning": "معدل النجاح يحتاج متابعة.",
            "is-danger": "معدل النجاح منخفض ويحتاج تدخلًا.",
        },
        "cumulative_gpa": {
            "is-neutral": "متوسط المعدل التراكمي المسجل في صف المتوسط.",
        },
        "progress": {
            "is-good": "تقدم أكاديمي جيد.",
            "is-warning": "التقدم الأكاديمي يحتاج متابعة.",
            "is-danger": "التقدم الأكاديمي منخفض.",
        },
        "retention": {
            "is-good": "معدل بقاء جيد.",
            "is-warning": "معدل البقاء يحتاج متابعة.",
            "is-danger": "معدل البقاء منخفض.",
        },
        "flow": {
            "is-good": "تدفق ونمو جيد.",
            "is-warning": "معدل التدفق يحتاج متابعة.",
            "is-danger": "معدل التدفق منخفض.",
        },
        "withdrawal": {
            "is-good": "معدل الانسحاب ضمن مستوى منخفض.",
            "is-warning": "معدل الانسحاب يحتاج متابعة.",
            "is-danger": "معدل الانسحاب مرتفع.",
        },
    }

    return notes.get(metric_key, {}).get(class_name, "")


def _empty_student_accumulator():
    return {
        "files_count": 0,
        "male_students": 0,
        "female_students": 0,
        "fallback_students": 0,
        "levels": {},
        "graduates": {},
        "rates": {
            "success": [],
            "cumulative_gpa": [],
            "progress": [],
            "retention": [],
            "flow": [],
            "withdrawal": [],
        },
        "gpa_weighted_sum": 0.0,
        "gpa_weight": 0,
        "exact_withdrawn": 0,
        "has_exact_withdrawn": False,
        "estimated_withdrawn": 0.0,
        "student_faculty_ratios": [],
        "fallback_gpa_values": [],
    }


def _add_file_to_student_accumulator(accumulator, evaluation_file):
    if not evaluation_file:
        return

    accumulator["files_count"] += 1

    level_rows = list(
        StudentLevelCount.objects
        .filter(evaluation_file=evaluation_file)
        .order_by("id")
    )

    file_male = 0
    file_female = 0

    for row in level_rows:
        level_name = str(row.level_name or "غير محدد").strip()
        male = int(row.male_count or 0)
        female = int(row.female_count or 0)

        file_male += male
        file_female += female

        level_item = accumulator["levels"].setdefault(
            level_name,
            {
                "level_name": level_name,
                "male": 0,
                "female": 0,
            },
        )

        level_item["male"] += male
        level_item["female"] += female

    accumulator["male_students"] += file_male
    accumulator["female_students"] += file_female

    standard1_data = _get_standard_form_data(evaluation_file, 1)
    standard5_data = _get_standard_form_data(evaluation_file, 5)

    if not level_rows:
        accumulator["fallback_students"] += _student_int(
            standard1_data.get("current_students_count")
        )

    success_rate = _get_rate_value(
        standard5_data,
        "average_success_rate",
        "male_success_rate",
        "female_success_rate",
        "success_rate",
    )

    cumulative_gpa = _get_rate_value(
        standard5_data,
        "average_cumulative_gpa",
        "male_cumulative_gpa",
        "female_cumulative_gpa",
        "cumulative_gpa",
    )

    progress_rate = _get_rate_value(
        standard5_data,
        "average_progress_rate",
        "male_progress_rate",
        "female_progress_rate",
        "progress_rate",
    )

    retention_rate = _get_rate_value(
        standard5_data,
        "average_retention_rate",
        "male_retention_rate",
        "female_retention_rate",
        "retention_rate",
    )

    flow_rate = _get_rate_value(
        standard5_data,
        "average_flow_rate",
        "male_flow_rate",
        "female_flow_rate",
        "growth_rate",
        "flow_rate",
    )

    withdrawal_rate = _get_rate_value(
        standard5_data,
        "average_withdrawal_rate",
        "male_withdrawal_rate",
        "female_withdrawal_rate",
        "withdrawal_rate",
    )

    student_faculty_ratio = _parse_student_faculty_ratio(
        standard5_data.get("student_faculty_ratio")
    )

    if student_faculty_ratio is not None:
        accumulator["student_faculty_ratios"].append(
            student_faculty_ratio
        )

    fallback_gpa = _student_number(
        standard5_data.get("graduates_gpa_average")
    )

    if fallback_gpa is None:
        fallback_gpa = _student_number(
            standard5_data.get("graduates_gpa")
        )

    if fallback_gpa is not None:
        accumulator["fallback_gpa_values"].append(
            fallback_gpa
        )

    for key, value in (
        ("success", success_rate),
        ("cumulative_gpa", cumulative_gpa),
        ("progress", progress_rate),
        ("retention", retention_rate),
        ("flow", flow_rate),
        ("withdrawal", withdrawal_rate),
    ):
        if value is not None:
            accumulator["rates"][key].append(value)

    file_total_students = file_male + file_female

    if not file_total_students:
        file_total_students = _student_int(
            standard1_data.get("current_students_count")
        )

    exact_withdrawn = _student_number(
        standard5_data.get("withdrawn_students_count")
    )

    if exact_withdrawn is None:
        exact_withdrawn = _student_number(
            standard5_data.get("withdrawal_count")
        )

    if exact_withdrawn is not None:
        accumulator["exact_withdrawn"] += int(round(exact_withdrawn))
        accumulator["has_exact_withdrawn"] = True
    elif withdrawal_rate is not None and file_total_students:
        accumulator["estimated_withdrawn"] += (
            file_total_students * withdrawal_rate / 100
        )

    graduate_rows = list(
        GraduateRecord.objects
        .filter(evaluation_file=evaluation_file)
        .order_by("academic_year", "id")
    )

    for row in graduate_rows:
        academic_year = str(row.academic_year or "غير محددة").strip()
        graduates_count = int(row.graduates_count or 0)
        gpa = _student_number(row.cumulative_gpa)

        graduate_item = accumulator["graduates"].setdefault(
            academic_year,
            {
                "academic_year": academic_year,
                "graduates_count": 0,
                "gpa_weighted_sum": 0.0,
                "gpa_weight": 0,
            },
        )

        graduate_item["graduates_count"] += graduates_count

        if gpa is not None:
            weight = graduates_count if graduates_count > 0 else 1

            graduate_item["gpa_weighted_sum"] += gpa * weight
            graduate_item["gpa_weight"] += weight

            accumulator["gpa_weighted_sum"] += gpa * weight
            accumulator["gpa_weight"] += weight


def _build_student_analysis(evaluation_files):
    unique_files = []
    seen_ids = set()

    for evaluation_file in evaluation_files or []:
        if not evaluation_file:
            continue

        if evaluation_file.id in seen_ids:
            continue

        seen_ids.add(evaluation_file.id)
        unique_files.append(evaluation_file)

    accumulator = _empty_student_accumulator()

    for evaluation_file in unique_files:
        _add_file_to_student_accumulator(
            accumulator,
            evaluation_file,
        )

    male_students = accumulator["male_students"]
    female_students = accumulator["female_students"]
    table_total_students = male_students + female_students

    total_students = (
        table_total_students
        if table_total_students > 0
        else accumulator["fallback_students"]
    )

    male_percentage = (
        _percentage(male_students, table_total_students)
        if table_total_students
        else 0
    )

    female_percentage = (
        _percentage(female_students, table_total_students)
        if table_total_students
        else 0
    )

    levels = []

    for item in accumulator["levels"].values():
        total = item["male"] + item["female"]

        levels.append({
            "level_name": item["level_name"],
            "male": item["male"],
            "female": item["female"],
            "total": total,
        })

    max_level_total = max(
        [item["total"] for item in levels] or [0]
    )

    for item in levels:
        item["total_width"] = (
            _percentage(item["total"], max_level_total)
            if max_level_total
            else 0
        )

        item["male_share"] = (
            _percentage(item["male"], item["total"])
            if item["total"]
            else 0
        )

        item["female_share"] = (
            _percentage(item["female"], item["total"])
            if item["total"]
            else 0
        )

    rate_definitions = [
        {
            "key": "success",
            "label": "معدل النجاح",
            "is_percentage": True,
        },
        {
            "key": "cumulative_gpa",
            "label": "المعدل التراكمي",
            "is_percentage": True,
},
        {
            "key": "progress",
            "label": "معدل التقدم",
            "is_percentage": True,
        },
        {
            "key": "retention",
            "label": "معدل البقاء",
            "is_percentage": True,
        },
        {
            "key": "flow",
            "label": "معدل التدفق / النمو",
            "is_percentage": True,
        },
        {
            "key": "withdrawal",
            "label": "معدل الانسحاب",
            "is_percentage": True,
        },
    ]

    rates = []
    rate_values = {}

    for definition in rate_definitions:
        metric_key = definition["key"]
        label = definition["label"]
        is_percentage = definition["is_percentage"]

        value = _student_average(
            accumulator["rates"][metric_key]
        )

        rate_values[metric_key] = value

        if value is None:
            display = "غير مسجل"
            bar_width = 0
            class_name = "is-empty"
            note = "لم يتم إدخال هذه القيمة في ملف البيانات."
        else:
            display = (
                _student_display(value)
                if is_percentage
                else f"{float(value):.2f}"
            )

            bar_width = (
                round(max(0, min(float(value), 100)), 2)
                if is_percentage
                else 0
            )

            class_name = _student_rate_class(
                metric_key,
                value,
            )

            note = _student_rate_note(
                metric_key,
                value,
            )

        rates.append({
            "key": metric_key,
            "label": label,
            "value": (
                round(value, 2)
                if value is not None
                else None
            ),
            "display": display,
            "bar_width": bar_width,
            "class_name": class_name,
            "note": note,
            "is_percentage": is_percentage,
        })

    graduates = []

    for item in accumulator["graduates"].values():
        average_gpa = None

        if item["gpa_weight"]:
            average_gpa = (
                item["gpa_weighted_sum"]
                / item["gpa_weight"]
            )

        graduates.append({
            "academic_year": item["academic_year"],
            "graduates_count": item["graduates_count"],
            "average_gpa": (
                f"{average_gpa:.2f}"
                if average_gpa is not None
                else ""
            ),
        })

    graduates.sort(
        key=lambda item: _extract_year_start(
            item["academic_year"]
        )
    )

    max_graduates = max(
        [item["graduates_count"] for item in graduates] or [0]
    )

    for item in graduates:
        item["bar_width"] = (
            _percentage(
                item["graduates_count"],
                max_graduates,
            )
            if max_graduates
            else 0
        )

    total_graduates = sum(
        item["graduates_count"]
        for item in graduates
    )

    average_gpa = None

    if accumulator["gpa_weight"]:
        average_gpa = (
            accumulator["gpa_weighted_sum"]
            / accumulator["gpa_weight"]
        )
    elif accumulator["fallback_gpa_values"]:
        average_gpa = _student_average(
            accumulator["fallback_gpa_values"]
        )

    student_faculty_ratio = _student_average(
        accumulator["student_faculty_ratios"]
    )

    if accumulator["has_exact_withdrawn"]:
        withdrawn_students = accumulator["exact_withdrawn"]
        withdrawn_is_estimated = False
    else:
        withdrawn_students = int(
            round(accumulator["estimated_withdrawn"])
        )
        withdrawn_is_estimated = True

    withdrawal_rate = rate_values.get("withdrawal")

    has_rates_data = any(
        item["value"] is not None
        for item in rates
    )

    has_data = any([
        has_rates_data,
        total_graduates,
        graduates,
    ])

    percentage_metrics = [
        item
        for item in rates
        if item["is_percentage"]
        and item["value"] is not None
        and item["key"] != "withdrawal"
    ]

    best_metric = (
        max(
            percentage_metrics,
            key=lambda item: item["value"],
        )
        if percentage_metrics
        else None
    )

    weakest_metric = (
        min(
            percentage_metrics,
            key=lambda item: item["value"],
        )
        if percentage_metrics
        else None
    )

    withdrawal_metric = next(
        (
            item
            for item in rates
            if item["key"] == "withdrawal"
        ),
        None,
    )

    return {
        "has_data": bool(has_data),
        "has_rates_data": has_rates_data,
        "is_aggregate": len(unique_files) > 1,
        "source_files_count": len(unique_files),

        "total_students": total_students,
        "male_students": male_students,
        "female_students": female_students,
        "male_percentage": f"{male_percentage:.2f}",
        "female_percentage": f"{female_percentage:.2f}",

        "total_graduates": total_graduates,
        "average_gpa": (
            f"{average_gpa:.2f}"
            if average_gpa is not None
            else ""
        ),

        "withdrawn_students": withdrawn_students,
        "withdrawn_is_estimated": withdrawn_is_estimated,
        "withdrawal_rate_display": _student_display(
            withdrawal_rate
        ),

        "student_faculty_ratio": student_faculty_ratio,
        "student_faculty_ratio_display": (
            _student_faculty_ratio_display(
                student_faculty_ratio
            )
        ),

        "rates": rates,
        "best_metric": best_metric,
        "weakest_metric": weakest_metric,
        "withdrawal_metric": withdrawal_metric,

        # تبقى البيانات الأخرى متاحة للخدمات اللاحقة،
        # بينما تركز لوحة التحليل الحالية على مؤشرات الأداء الستة.
        "levels": levels,
        "graduates": graduates,
    }



# ============================================================
# بناء السياق الرئيسي
# ============================================================

def build_analysis_context(request):
    selected_file_id = request.GET.get("file_id")
    selected_program_id = request.GET.get("program_id", "all")
    selected_academic_year = request.GET.get("academic_year")

    current_user = _current_user_or_none(request)

    selected_status = request.GET.get("status", "all")
    selected_analysis_mode = request.GET.get("mode", "followup")
    selected_detail_sort = request.GET.get("detail_sort", "weakest")

    allowed_statuses = {"all", "reviewed", "draft", "empty"}
    if selected_status not in allowed_statuses:
        selected_status = "all"

    allowed_modes = {"followup", "official"}
    if selected_analysis_mode not in allowed_modes:
        selected_analysis_mode = "followup"

    allowed_detail_sorts = {"weakest", "strongest", "priority"}
    if selected_detail_sort not in allowed_detail_sorts:
        selected_detail_sort = "weakest"

    academic_year_options = _get_academic_year_options()

    (
        program_options,
        id_to_canonical_program,
    ) = _get_canonical_program_data()

    selected_program_id = _canonical_program_id(
        selected_program_id,
        id_to_canonical_program,
    )

    program_years_map = _get_program_years_map(
        id_to_canonical_program
    )

    evaluation_files = (
        EvaluationFile.objects
        .select_related("program")
        .exclude(status="template_preview")
        .order_by("-updated_at")
    )

    selected_file = None
    review = None
    reviews_for_scope = []

    if selected_file_id:
        selected_file = get_object_or_404(
            EvaluationFile.objects.select_related("program"),
            id=selected_file_id,
        )

        selected_program_id = _canonical_program_id(
            selected_file.program_id,
            id_to_canonical_program,
        )
        selected_academic_year = selected_file.academic_year

        review = _get_review_for_file(selected_file)

        if not review:
            review = generate_auto_review(
                selected_file,
                current_user,
            )

    if not selected_academic_year:
        if academic_year_options:
            selected_academic_year = academic_year_options[0]
        else:
            latest_review = _get_latest_review()
            if latest_review:
                selected_academic_year = latest_review.evaluation_file.academic_year

    # عند اختيار برنامج معين، لا نسمح بسنة غير محفوظة لهذا البرنامج،
    # مع إبقاء خيار كل السنوات متاحًا دائمًا.
    available_years_for_selected_program = _available_years_for_program(
        program_years_map,
        selected_program_id,
        academic_year_options,
    )

    if (
        selected_program_id
        and selected_program_id != "all"
        and selected_academic_year
        and selected_academic_year != "all"
        and selected_academic_year not in available_years_for_selected_program
    ):
        selected_academic_year = "all"

    is_all_programs = (
        not selected_program_id
        or selected_program_id == "all"
    )

    is_all_years = selected_academic_year == "all"
    is_aggregate_analysis = is_all_programs or is_all_years

    if not is_all_programs and not is_all_years and not review:
        selected_file = _get_file_for_program_and_year(
            program_id=selected_program_id,
            academic_year=selected_academic_year,
        )

        if selected_file:
            review = _get_review_for_file(selected_file)

            if not review:
                review = generate_auto_review(
                    selected_file,
                    current_user,
                )

    if is_aggregate_analysis:
        reviews_for_scope = _get_reviews_for_scope(
            academic_year=selected_academic_year,
            program_id=selected_program_id,
            user=current_user,
        )

    has_analysis = bool(review) or bool(reviews_for_scope)

    rows = []
    all_rows = []
    summary = None
    recommendations = []
    insights = None

    approval_indicator = None
    performance_bars = []
    smart_priorities = []
    temporal_comparison = None
    program_comparison = None
    detailed_rows = []
    analysis_reading = None
    calculation_explanation = []

    can_issue_official = False
    official_blockers_count = 0

    if is_aggregate_analysis and reviews_for_scope:
        all_rows = _build_aggregate_standard_rows(
            reviews=reviews_for_scope,
            selected_status="all",
        )

        rows = _build_aggregate_standard_rows(
            reviews=reviews_for_scope,
            selected_status=selected_status,
        )

        summary = _build_summary_from_reviews(
            reviews=reviews_for_scope,
            rows=all_rows,
        )

        official_blockers_count = (
            summary["draft_count"] + summary["needs_review_count"]
        )

        can_issue_official = (
            summary["total_reviews"] > 0
            and official_blockers_count == 0
        )

        approval_indicator = _build_approval_indicator(
            summary=summary,
            can_issue_official=can_issue_official,
            is_aggregate_analysis=True,
        )

        recommendations = _build_recommendations(
            rows=all_rows,
            summary=summary,
            is_aggregate_analysis=True,
        )

        insights = _build_insights(
            rows=all_rows,
            summary=summary,
            selected_analysis_mode=selected_analysis_mode,
            can_issue_official=can_issue_official,
            is_aggregate_analysis=True,
        )

        performance_bars = _build_performance_bars(all_rows)
        smart_priorities = _build_smart_priorities(all_rows)

        if is_all_years:
            temporal_comparison = {
                "has_previous": False,
                "current_year": "كل السنوات",
                "previous_year": "",
                "overall_difference": None,
                "overall_trend_label": "غير متاح",
                "overall_trend_class": "is-neutral",
                "rows": [],
                "message": "تم اختيار كل السنوات؛ اختاري سنة محددة لعرض المقارنة الزمنية بين عامين.",
            }
        else:
            temporal_comparison = _build_temporal_comparison_for_all_programs(
                current_year=selected_academic_year,
                current_rows=all_rows,
                current_summary=summary,
                academic_year_options=academic_year_options,
                user=current_user,
            )

        program_comparison = _build_program_comparison_by_scope(
            academic_year=selected_academic_year,
            user=current_user,
        )

        detailed_rows = _build_detailed_rows(
            rows=all_rows,
            sort_mode=selected_detail_sort,
        )

        analysis_reading = _build_analysis_reading(
            rows=all_rows,
            summary=summary,
            priority_rows=smart_priorities,
            is_aggregate_analysis=True,
        )

        calculation_explanation = _build_calculation_explanation(
            summary=summary,
            is_aggregate_analysis=True,
            is_all_programs=is_all_programs,
            is_all_years=is_all_years,
        )

    elif review:
        all_rows = _build_standard_rows(
            review=review,
            selected_status="all",
        )

        rows = _build_standard_rows(
            review=review,
            selected_status=selected_status,
        )

        summary = _build_summary_from_review(
            review=review,
            rows=all_rows,
        )

        official_blockers_count = (
            summary["draft_count"] + summary["needs_review_count"]
        )

        can_issue_official = (
            summary["total_standards"] > 0
            and official_blockers_count == 0
        )

        approval_indicator = _build_approval_indicator(
            summary=summary,
            can_issue_official=can_issue_official,
            is_aggregate_analysis=False,
        )

        recommendations = _build_recommendations(
            rows=all_rows,
            summary=summary,
            is_aggregate_analysis=False,
        )

        if selected_analysis_mode == "official" and not can_issue_official:
            recommendations.insert(
                0,
                "لا يمكن اعتماد هذا التحليل كتقرير رسمي حاليًا؛ يجب اعتماد جميع المعايير أولًا قبل إصدار الحكم النهائي."
            )

        insights = _build_insights(
            rows=all_rows,
            summary=summary,
            selected_analysis_mode=selected_analysis_mode,
            can_issue_official=can_issue_official,
            is_aggregate_analysis=False,
        )

        performance_bars = _build_performance_bars(all_rows)
        smart_priorities = _build_smart_priorities(all_rows)

        temporal_comparison = _build_temporal_comparison_for_review(
            review=review,
            current_rows=all_rows,
            current_summary=summary,
            academic_year_options=academic_year_options,
        )

        program_comparison = _build_program_comparison_by_scope(
            academic_year=selected_academic_year,
            user=current_user,
        )

        detailed_rows = _build_detailed_rows(
            rows=all_rows,
            sort_mode=selected_detail_sort,
        )

        analysis_reading = _build_analysis_reading(
            rows=all_rows,
            summary=summary,
            priority_rows=smart_priorities,
            is_aggregate_analysis=False,
        )

        calculation_explanation = _build_calculation_explanation(
            summary=summary,
            is_aggregate_analysis=False,
            is_all_programs=is_all_programs,
            is_all_years=is_all_years,
        )

    analysis_student_files = []

    if is_aggregate_analysis and reviews_for_scope:
        analysis_student_files = [
            item.evaluation_file
            for item in reviews_for_scope
            if item and item.evaluation_file
        ]
    elif selected_file:
        analysis_student_files = [selected_file]
    elif review and review.evaluation_file:
        analysis_student_files = [review.evaluation_file]

    student_analysis = _build_student_analysis(
        analysis_student_files
    )

    analysis_scope_label = "كل البرامج والتخصصات" if is_all_programs else "برنامج محدد"

    return {
        "page_title": "تحليل التقييمات الأكاديمية",

        "evaluation_files": evaluation_files,
        "program_options": program_options,
        "academic_year_options": academic_year_options,
        "program_years_map": program_years_map,
        "available_years_for_selected_program": available_years_for_selected_program,

        "selected_file": selected_file,
        "selected_file_id": str(selected_file.id) if selected_file else "",

        "selected_program_id": selected_program_id,
        "selected_academic_year": selected_academic_year,
        "selected_status": selected_status,

        "selected_analysis_mode": selected_analysis_mode,
        "selected_detail_sort": selected_detail_sort,

        "is_all_programs": is_all_programs,
        "is_all_years": is_all_years,
        "is_aggregate_analysis": is_aggregate_analysis,
        "analysis_scope_label": analysis_scope_label,

        "can_issue_official": can_issue_official,
        "official_blockers_count": official_blockers_count,

        "review": review,
        "has_analysis": has_analysis,

        "summary": summary,
        "standard_rows": rows,
        "recommendations": recommendations,
        "insights": insights,

        "approval_indicator": approval_indicator,
        "performance_bars": performance_bars,
        "smart_priorities": smart_priorities,
        "temporal_comparison": temporal_comparison,
        "program_comparison": program_comparison,
        "detailed_rows": detailed_rows,
        "analysis_reading": analysis_reading,
        "calculation_explanation": calculation_explanation,
        "student_analysis": student_analysis,

        "analysis_mode_options": [
            ("followup", "قراءة متابعة"),
            ("official", "قراءة نهائية للاعتماد"),
        ],

        "status_options": [
            ("all", "كل المعايير"),
            ("reviewed", "المعايير المعتمدة فقط"),
            ("draft", "المسودات فقط"),
            ("empty", "غير المكتملة فقط"),
        ],

        "detail_sort_options": [
            ("weakest", "الأضعف أولًا"),
            ("strongest", "الأقوى أولًا"),
            ("priority", "الأكثر أولوية للتحسين"),
        ],
    }

