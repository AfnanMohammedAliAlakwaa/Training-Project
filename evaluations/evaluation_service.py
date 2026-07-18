from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .evaluation_rules import STANDARD_EVALUATION_RULES

from .models import (
    ProgramEvaluationReview,
    StandardEvaluationReview,
    IndicatorEvaluationReview,
)

from dashboard.models import (
    CourseRecord,
    DataEntryTableRecord,
    EducationProcessRecord,
    EvidenceAttachment,
    FacultyMemberRecord,
    GraduateRecord,
    InfrastructureRecord,
    LibrarySourceRecord,
    QualityStandard,
    StandardEntry,
    StudentLevelCount,
)


# ============================================================
# أدوات عامة
# ============================================================

def clean_text(value):
    return str(value or "").strip()


def to_decimal(value, default="0"):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def decimal_round(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def value_has_content(value):
    if value is None:
        return False

    if isinstance(value, dict):
        return any(value_has_content(item) for item in value.values())

    if isinstance(value, list):
        return any(value_has_content(item) for item in value)

    return clean_text(value) != ""


def score_label(score):
    labels = {
        5: "مستوفي بتميز",
        4: "مستوفي بإتقان",
        3: "مستوفي",
        2: "مستوفي جزئيًا",
        1: "غير مستوفي",
    }

    return labels.get(int(score or 1), "غير مستوفي")


def score_from_percentage(percentage):
    percentage = Decimal(str(percentage or 0))

    if percentage >= 90:
        return 5

    if percentage >= 80:
        return 4

    if percentage >= 65:
        return 3

    if percentage >= 40:
        return 2

    return 1


def percentage_from_score(score):
    score = int(score or 1)
    return decimal_round((Decimal(score) / Decimal(5)) * Decimal(100))


def indicator_included_in_reviewer_calculation(indicator_review):
    """
    تحديد هل يدخل المؤشر في حساب درجة المراجع العامة.

    المؤشر المرتبط بالمرفقات فقط لا يدخل في الحساب إطلاقًا،
    حتى لو اختار المراجع له درجة يدوية. تبقى الدرجة محفوظة
    للعرض والتوثيق فقط دون أن تخفض أو ترفع نتيجة المعيار.
    """

    snapshot = indicator_review.data_snapshot

    if not isinstance(snapshot, dict):
        # توافق مع السجلات القديمة التي قد لا تحتوي على snapshot.
        return True

    return snapshot.get("included_in_standard", True) is not False


def calculate_reviewer_result_from_indicators(indicator_reviews):
    """
    حساب نتيجة المراجع العامة للمعيار من درجات المؤشرات اليدوية.

    لا تدخل المؤشرات التوثيقية المرتبطة بالمرفقات فقط في المتوسط.
    تُحفظ درجة المراجع عليها للعرض، لكنها لا تؤثر على النتيجة.
    """

    reviewer_scores = [
        Decimal(str(indicator_review.reviewer_score))
        for indicator_review in indicator_reviews
        if (
            indicator_review.reviewer_score is not None
            and indicator_included_in_reviewer_calculation(
                indicator_review
            )
        )
    ]

    if not reviewer_scores:
        return None

    reviewer_percentage = decimal_round(
        (
            sum(reviewer_scores)
            / (Decimal(len(reviewer_scores)) * Decimal("5"))
        )
        * Decimal("100")
    )

    return {
        "reviewer_score": score_from_percentage(reviewer_percentage),
        "reviewer_percentage": reviewer_percentage,
    }


def parse_score(value):
    value = clean_text(value)

    if not value:
        return None

    try:
        score = int(value)
    except ValueError:
        return None

    if score in [1, 2, 3, 4, 5]:
        return score

    return None


def current_user_or_none(request):
    if hasattr(request, "user") and request.user.is_authenticated:
        return request.user

    return None


# ============================================================
# قراءة بيانات الإدخال والأدلة
# ============================================================

def get_entry(evaluation_file, standard_number):
    return (
        StandardEntry.objects
        .filter(
            evaluation_file=evaluation_file,
            standard__number=standard_number,
        )
        .select_related("standard")
        .first()
    )


def get_form_data(evaluation_file, standard_number):
    entry = get_entry(evaluation_file, standard_number)

    if not entry or not isinstance(entry.form_data, dict):
        return {}

    return entry.form_data


def form_table_has_rows(form_data, table_key):
    rows = form_data.get(table_key, [])

    if not isinstance(rows, list):
        return False

    return any(value_has_content(row) for row in rows)


def dynamic_table_has_rows(evaluation_file, table_key):
    return (
        DataEntryTableRecord.objects
        .filter(evaluation_file=evaluation_file, table_key=table_key)
        .exclude(rows=[])
        .exists()
    )


def attachment_exists(evaluation_file, standard_number, title):
    title = clean_text(title)

    if not title:
        return False

    return EvidenceAttachment.objects.filter(
        standard_entry__evaluation_file=evaluation_file,
        standard_entry__standard__number=standard_number,
        title=title,
    ).exists()


def record_check_exists(evaluation_file, check_key):
    if check_key == "courses":
        return CourseRecord.objects.filter(
            evaluation_file=evaluation_file
        ).exists()

    if check_key == "course_specs":
        return (
            CourseRecord.objects
            .filter(evaluation_file=evaluation_file)
            .filter(
                Q(requirement_type="course_specification")
                | Q(has_specification=True)
            )
            .exists()
        )

    if check_key == "faculty":
        return (
            FacultyMemberRecord.objects
            .filter(evaluation_file=evaluation_file)
            .exclude(name="")
            .exclude(name__isnull=True)
            .exists()
    )

    if check_key == "student_levels":
        return (
            StudentLevelCount.objects
            .filter(evaluation_file=evaluation_file)
            .filter(
                Q(male_count__gt=0)
                | Q(female_count__gt=0)
        )
        .exists()
    )

    if check_key == "graduates":
        return (
            GraduateRecord.objects
            .filter(evaluation_file=evaluation_file)
            .filter(
                Q(graduates_count__gt=0)
                | Q(male_count__gt=0)
                | Q(female_count__gt=0)
        )
        .exists()
    )

    if check_key == "infrastructure":
        return InfrastructureRecord.objects.filter(
            evaluation_file=evaluation_file
        ).exists()

    if check_key == "library_sources":
        return LibrarySourceRecord.objects.filter(
            evaluation_file=evaluation_file
        ).exists()

    if check_key == "education_process":
        return EducationProcessRecord.objects.filter(
            evaluation_file=evaluation_file
        ).exists()

    return False


# ============================================================
# التقييم الآلي
# ============================================================

def evaluate_indicator(evaluation_file, standard_number, indicator):
    """
    تقييم المؤشر اعتمادًا على البيانات المدخلة فقط.

    المرفقات:
    - تُحفظ في النظام كشواهد ووثائق.
    - لا تدخل في total_checks.
    - لا ترفع الدرجة عند وجودها.
    - لا تخفض الدرجة عند عدم وجودها.
    """
    form_data = get_form_data(evaluation_file, standard_number)

    total_checks = 0
    passed_checks = 0

    missing_items = []
    passed_items = []

    # الاحتفاظ بأسماء المرفقات للتوثيق فقط
    ignored_attachments = [
        clean_text(title)
        for title in indicator.get("attachments", [])
        if clean_text(title)
    ]

    # ========================================================
    # الحقول العادية
    # ========================================================

    for field_name in indicator.get("fields", []):
        total_checks += 1

        if value_has_content(form_data.get(field_name)):
            passed_checks += 1
            passed_items.append(field_name)
        else:
            missing_items.append(
                f"الحقل غير مكتمل: {field_name}"
            )

    # ========================================================
    # الحقول التي يجب أن تطابق قيمة محددة
    # مثال: has_psd يجب أن تكون قيمته "نعم"
    # ========================================================

    for field_name, allowed_values in indicator.get("field_values", {}).items():
        total_checks += 1

        current_value = clean_text(
            form_data.get(field_name)
        )

        normalized_allowed_values = {
            clean_text(allowed_value)
            for allowed_value in allowed_values
        }

        if current_value in normalized_allowed_values:
            passed_checks += 1
            passed_items.append(field_name)
        else:
            expected_values = "، ".join(
                sorted(normalized_allowed_values)
            )

            missing_items.append(
                f"القيمة غير مستوفاة: {field_name} "
                f"(المطلوب: {expected_values})"
            )

    # ========================================================
    # الجداول الموجودة داخل form_data
    # ========================================================

    for table_key in indicator.get("form_tables", []):
        total_checks += 1

        if form_table_has_rows(form_data, table_key):
            passed_checks += 1
            passed_items.append(table_key)
        else:
            missing_items.append(
                f"الجدول غير مكتمل: {table_key}"
            )

    # ========================================================
    # الجداول الديناميكية المحفوظة في قاعدة البيانات
    # ========================================================

    for table_key in indicator.get("dynamic_tables", []):
        total_checks += 1

        if dynamic_table_has_rows(
            evaluation_file,
            table_key,
        ):
            passed_checks += 1
            passed_items.append(table_key)
        else:
            missing_items.append(
                f"الجدول غير مكتمل: {table_key}"
            )

    # ========================================================
    # السجلات المنظمة المحفوظة في قاعدة البيانات
    # ========================================================

    for check_key in indicator.get("record_checks", []):
        total_checks += 1

        if record_check_exists(
            evaluation_file,
            check_key,
        ):
            passed_checks += 1
            passed_items.append(check_key)
        else:
            missing_items.append(
                f"لا توجد بيانات محفوظة في: {check_key}"
            )

    # ========================================================
    # المرفقات لا تُفحص ولا تدخل في الدرجة
    # ========================================================

    included_in_standard = total_checks > 0

    if not included_in_standard:
        percentage = Decimal("0")
        score = 1

        note = (
            "هذا مؤشر توثيقي مرتبط بالمرفقات فقط، "
            "ولذلك لا يدخل في حساب الدرجة الآلية."
        )

    else:
        percentage = decimal_round(
            (
                Decimal(passed_checks)
                / Decimal(total_checks)
            )
            * Decimal(100)
        )

        score = score_from_percentage(percentage)

        if passed_checks == total_checks:
            note = (
                "المؤشر مستوفى آليًا حسب البيانات "
                "المدخلة في النظام."
            )

        elif passed_checks == 0:
            note = (
                "المؤشر غير مستوفى؛ لا توجد بيانات "
                "مدخلة كافية."
            )

        else:
            note = (
                "المؤشر مستوفى جزئيًا؛ توجد بيانات "
                "ناقصة تحتاج إلى استكمال."
            )

        if missing_items:
            note += (
                " النواقص: "
                + " | ".join(missing_items)
            )

    if ignored_attachments:
        note += (
            " المرفقات المرتبطة بهذا المؤشر "
            "توثيقية فقط ولا تدخل في الدرجة."
        )

    return {
        "score": score,
        "percentage": percentage,
        "note": note,

        # مهم: لمنع المؤشر الذي لا يحتوي إلا على مرفقات
        # من تخفيض متوسط المعيار.
        "included_in_standard": included_in_standard,

        "snapshot": {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "passed_items": passed_items,
            "missing_items": missing_items,

            "included_in_standard": included_in_standard,
            "ignored_attachments": ignored_attachments,
        },
    }


def get_or_create_quality_standard(rule):
    """
    إنشاء المعيار عند عدم وجوده فقط.

    بعد إنشاء المعيار تصبح قاعدة البيانات هي المصدر
    الرئيسي للعنوان والوزن والحالة، ولا تعيد قواعد
    التقييم الآلي الكتابة فوق تعديلات لوحة الإدارة.
    """

    standard, created = QualityStandard.objects.get_or_create(
        number=rule["number"],
        defaults={
            "title": rule["title"],
            "weight": rule.get("weight", 0),
            "is_active": True,
        },
    )

    return standard


def calculate_standard_auto_result(indicator_results):
    """
    حساب نتيجة المعيار من مؤشرات البيانات فقط.

    المؤشرات المرتبطة بالمرفقات فقط يتم استبعادها
    من المتوسط بدل احتسابها بصفر.
    """
    evaluable_results = [
        item
        for item in indicator_results
        if item.get("included_in_standard", True)
    ]

    ignored_count = (
        len(indicator_results)
        - len(evaluable_results)
    )

    if not evaluable_results:
        return {
            "auto_percentage": Decimal("0"),
            "auto_score": 1,
            "auto_notes": (
                "لا توجد قواعد بيانات قابلة للحساب "
                "لهذا المعيار. المرفقات لا تدخل في الدرجة."
            ),
        }

    percentages = [
        to_decimal(item["percentage"])
        for item in evaluable_results
    ]

    average_percentage = decimal_round(
        sum(percentages)
        / Decimal(len(percentages))
    )

    auto_score = score_from_percentage(
        average_percentage
    )

    weak_count = len([
        item
        for item in evaluable_results
        if int(item["score"]) <= 2
    ])

    complete_count = len([
        item
        for item in evaluable_results
        if int(item["score"]) >= 4
    ])

    notes = (
        f"تم فحص {len(evaluable_results)} مؤشر "
        f"اعتمادًا على البيانات المدخلة فقط. "
        f"عدد المؤشرات القوية: {complete_count}. "
        f"عدد المؤشرات الضعيفة: {weak_count}."
    )

    if ignored_count:
        notes += (
            f" تم استبعاد {ignored_count} مؤشر "
            f"توثيقي مرتبط بالمرفقات من الحساب."
        )

    return {
        "auto_percentage": average_percentage,
        "auto_score": auto_score,
        "auto_notes": notes,
    }


# ============================================================
# هل يوجد إدخال فعلي من المراجع؟
# ============================================================

def indicator_has_reviewer_input(indicator_review):
    return (
        indicator_review.reviewer_score is not None
        or value_has_content(indicator_review.reviewer_notes)
    )


def standard_has_reviewer_input(standard_review):
    has_standard_input = (
        standard_review.reviewer_score is not None
        or value_has_content(standard_review.reviewer_notes)
        or value_has_content(standard_review.strengths)
        or value_has_content(standard_review.weaknesses)
        or value_has_content(standard_review.improvement_plan)
        or value_has_content(standard_review.execution_time)
    )

    if has_standard_input:
        return True

    return standard_review.indicator_reviews.filter(
        Q(reviewer_score__isnull=False)
        | ~Q(reviewer_notes="")
    ).exists()


def standard_status_label(status):
    labels = {
        "empty": "بحاجة إلى مراجعة",
        "draft": "مسودة",
        "reviewed": "معتمد",
    }

    return labels.get(status, "بحاجة إلى مراجعة")


# ============================================================
# الحسابات النهائية
# ============================================================

def recalculate_review_totals(review):
    standard_reviews = (
        review.standard_reviews
        .select_related("standard")
        .all()
    )

    auto_total = Decimal("0")
    reviewer_total = Decimal("0")
    reviewer_has_any_score = False

    for standard_review in standard_reviews:
        auto_total += to_decimal(standard_review.auto_weighted_score)

        if standard_review.reviewer_score is not None:
            reviewer_has_any_score = True
            reviewer_total += to_decimal(standard_review.reviewer_weighted_score)
        else:
            reviewer_total += to_decimal(standard_review.auto_weighted_score)

    review.overall_auto_percentage = decimal_round(auto_total)

    if reviewer_has_any_score:
        review.overall_reviewer_percentage = decimal_round(reviewer_total)
        review.final_percentage = decimal_round(reviewer_total)
    else:
        review.overall_reviewer_percentage = None
        review.final_percentage = decimal_round(auto_total)

    review.final_status_label = score_label(
        score_from_percentage(review.final_percentage)
    )

    review.save(update_fields=[
        "overall_auto_percentage",
        "overall_reviewer_percentage",
        "final_percentage",
        "final_status_label",
        "updated_at",
    ])

    return review
def sync_review_weights(review):
    """
    مزامنة أوزان سجلات التقييم الموجودة مع الأوزان
    الحالية الموجودة في جدول معايير الجودة.

    لا تغيّر درجات المراجع أو ملاحظاته، وإنما تعيد
    حساب المساهمة الموزونة والنتيجة النهائية فقط.
    """

    has_changes = False

    standard_reviews = (
        review.standard_reviews
        .select_related("standard")
        .all()
    )

    for standard_review in standard_reviews:
        current_weight = to_decimal(
            standard_review.standard.weight or 0
        )

        stored_weight = to_decimal(
            standard_review.weight or 0
        )

        if stored_weight == current_weight:
            continue

        standard_review.weight = current_weight

        standard_review.auto_weighted_score = decimal_round(
            (
                to_decimal(
                    standard_review.auto_percentage
                )
                / Decimal("100")
            )
            * current_weight
        )

        update_fields = [
            "weight",
            "auto_weighted_score",
        ]

        if standard_review.reviewer_score is not None:
            reviewer_percentage = (
                standard_review.reviewer_percentage
            )

            if reviewer_percentage is None:
                reviewer_percentage = percentage_from_score(
                    standard_review.reviewer_score
                )

            standard_review.reviewer_percentage = (
                reviewer_percentage
            )

            standard_review.reviewer_weighted_score = decimal_round(
                (
                    to_decimal(reviewer_percentage)
                    / Decimal("100")
                )
                * current_weight
            )

            update_fields.extend([
                "reviewer_percentage",
                "reviewer_weighted_score",
            ])

        standard_review.save(
            update_fields=update_fields
        )

        has_changes = True

    if has_changes:
        recalculate_review_totals(review)

    return review

def refresh_program_review_status(review):
    """
    اعتماد التقييم العام لا يحدث إلا إذا كانت جميع المعايير معتمدة.

    أي حالة أخرى، مثل:
    - بعض المعايير معتمدة
    - بعض المعايير مسودات
    - وجود معايير غير محفوظة

    تعتبر تقييمًا غير مكتمل.
    """

    standard_reviews = review.standard_reviews.all()

    total_count = standard_reviews.count()

    reviewed_count = standard_reviews.filter(
        review_status="reviewed"
    ).count()

    # البرنامج معتمد فقط عندما تكون جميع المعايير معتمدة.
    all_standards_reviewed = (
        total_count > 0
        and reviewed_count == total_count
    )

    if all_standards_reviewed:
        review.status = "reviewed"
    else:
        review.status = "draft"
        review.reviewed_by = None

    review.save(
        update_fields=[
            "status",
            "reviewed_by",
            "updated_at",
        ]
    )

    return review


# ============================================================
# توليد / تحديث التقييم الآلي
# ============================================================
def _get_standard_rules_map():
    """
    ربط رقم المعيار بقاعدة التقييم الآلي الخاصة به.
    """
    return {
        int(rule["number"]): rule
        for rule in STANDARD_EVALUATION_RULES
    }


def build_dynamic_standard_rule(standard):
    """
    إنشاء قاعدة تقييم آلي احتياطية لأي معيار جديد
    تمت إضافته من لوحة الإدارة ولا توجد له قاعدة ثابتة.

    صفحة إدخال البيانات تنشئ للمعيار الديناميكي حقلًا باسم:
    standard_<رقم المعيار>_notes
    """

    standard_number = int(standard.number)

    return {
        "number": standard_number,
        "title": standard.title,
        "weight": standard.weight or 0,
        "is_dynamic": True,
        "indicators": [
            {
                "key": f"dynamic_standard_{standard_number}_data",
                "text": f"تتوفر بيانات مدخلة للمعيار: {standard.title}",
                "fields": [
                    f"standard_{standard_number}_notes",
                ],
            },
        ],
    }
@transaction.atomic
def generate_auto_review(evaluation_file, user=None):
    review, created = ProgramEvaluationReview.objects.get_or_create(
        evaluation_file=evaluation_file,
        defaults={
            "generated_by": (
                user
                if user and user.is_authenticated
                else None
            ),
            "status": "draft",
        },
    )

    if (
        user
        and user.is_authenticated
        and not review.generated_by
    ):
        review.generated_by = user
        review.save(
            update_fields=[
                "generated_by",
                "updated_at",
            ]
        )

    # نتأكد أولًا من وجود المعايير الأساسية المعرفة
    # داخل قواعد التقييم الآلي.
    for rule in STANDARD_EVALUATION_RULES:
        get_or_create_quality_standard(rule)

    rules_map = _get_standard_rules_map()

    # المصدر الأساسي أصبح جدول معايير الجودة.
    # أي معيار نشط يضاف من لوحة الإدارة سيظهر هنا.
    active_standards = (
        QualityStandard.objects
        .filter(is_active=True)
        .order_by("number", "id")
    )

    for standard in active_standards:
        rule = rules_map.get(
            int(standard.number)
        )

        if rule is None:
            rule = build_dynamic_standard_rule(
                standard
            )

        weight = to_decimal(
            standard.weight or 0
        )

        standard_review, standard_created = (
            StandardEvaluationReview.objects
            .get_or_create(
                review=review,
                standard=standard,
                defaults={
                    "weight": weight,
                    "review_status": "empty",
                },
            )
        )

        indicator_results = []
        current_indicator_keys = []

        # تقييم مؤشرات المعيار، سواء كانت قواعده ثابتة
        # أو قاعدة احتياطية لمعيار مضاف من الإدارة.
        for indicator in rule.get(
            "indicators",
            [],
        ):
            indicator_key = indicator["key"]

            current_indicator_keys.append(
                indicator_key
            )

            result = evaluate_indicator(
                evaluation_file,
                standard.number,
                indicator,
            )

            indicator_results.append(
                result
            )

            indicator_review, indicator_created = (
                IndicatorEvaluationReview.objects
                .get_or_create(
                    standard_review=standard_review,
                    indicator_key=indicator_key,
                    defaults={
                        "indicator_text": (
                            indicator["text"]
                        ),
                    },
                )
            )

            indicator_review.indicator_text = (
                indicator["text"]
            )

            indicator_review.auto_score = (
                result["score"]
            )

            indicator_review.auto_percentage = (
                result["percentage"]
            )

            indicator_review.auto_notes = (
                result["note"]
            )

            indicator_review.data_snapshot = (
                result["snapshot"]
            )

            indicator_review.save()

        # حذف مؤشرات آلية قديمة لم تعد موجودة
        # في قاعدة المعيار الحالية.
        if current_indicator_keys:
            (
                standard_review
                .indicator_reviews
                .exclude(
                    indicator_key__in=(
                        current_indicator_keys
                    )
                )
                .delete()
            )

        standard_result = (
            calculate_standard_auto_result(
                indicator_results
            )
        )

        auto_percentage = (
            standard_result["auto_percentage"]
        )

        auto_score = (
            standard_result["auto_score"]
        )

        standard_review.weight = weight
        standard_review.auto_score = auto_score
        standard_review.auto_percentage = (
            auto_percentage
        )

        standard_review.auto_weighted_score = (
            decimal_round(
                (
                    auto_percentage
                    / Decimal("100")
                )
                * weight
            )
        )

        standard_review.auto_notes = (
            standard_result["auto_notes"]
        )

        if rule.get("is_dynamic"):
            standard_review.auto_notes += (
                " تم تقييم هذا المعيار اعتمادًا على "
                "البيانات العامة المدخلة له من صفحة إدخال البيانات."
            )

        if (
            standard_review.reviewer_score
            is not None
        ):
            reviewer_percentage = (
                percentage_from_score(
                    standard_review.reviewer_score
                )
            )

            standard_review.reviewer_percentage = (
                reviewer_percentage
            )

            standard_review.reviewer_weighted_score = (
                decimal_round(
                    (
                        reviewer_percentage
                        / Decimal("100")
                    )
                    * weight
                )
            )

        standard_review.save()

    return recalculate_review_totals(
        review
    )


# ============================================================
# حفظ معيار واحد فقط
# ============================================================

def apply_standard_post_data(request, standard_review):
    score_field = f"standard_score_{standard_review.id}"
    notes_field = f"standard_notes_{standard_review.id}"
    strengths_field = f"strengths_{standard_review.id}"
    weaknesses_field = f"weaknesses_{standard_review.id}"
    improvement_field = f"improvement_plan_{standard_review.id}"
    execution_field = f"execution_time_{standard_review.id}"

    evaluation_mode = clean_text(
        request.POST.get("evaluation_mode", "manual")
    ).lower()

    submitted_standard_score = parse_score(
        request.POST.get(score_field, "")
    )

    standard_review.reviewer_notes = clean_text(
        request.POST.get(notes_field, "")
    )

    standard_review.strengths = clean_text(
        request.POST.get(strengths_field, "")
    )

    standard_review.weaknesses = clean_text(
        request.POST.get(weaknesses_field, "")
    )

    standard_review.improvement_plan = clean_text(
        request.POST.get(improvement_field, "")
    )

    standard_review.execution_time = clean_text(
        request.POST.get(execution_field, "")
    )

    indicator_reviews = list(
        standard_review.indicator_reviews.all()
    )

    indicator_score_modified = False

    # حفظ درجات وملاحظات المراجع لكل مؤشر أولًا.
    for indicator_review in indicator_reviews:
        indicator_score_field = (
            f"indicator_score_{indicator_review.id}"
        )
        indicator_notes_field = (
            f"indicator_notes_{indicator_review.id}"
        )

        indicator_score = parse_score(
            request.POST.get(indicator_score_field, "")
        )

        indicator_review.reviewer_score = indicator_score
        indicator_review.reviewer_notes = clean_text(
            request.POST.get(indicator_notes_field, "")
        )

        if (
            indicator_score is not None
            and indicator_score != indicator_review.auto_score
        ):
            indicator_score_modified = True

        indicator_review.save()

    # في وضع التقييم الآلي المعدل، تصبح درجات المؤشرات التي
    # عدلها أو اعتمدها المراجع هي المصدر لدرجة المعيار العامة.
    # أما في الوضع اليدوي فيبقى حقل درجة المعيار هو المصدر،
    # حتى لا يتغير السلوك اليدوي الحالي.
    reviewer_result = None

    if evaluation_mode == "auto":
        reviewer_result = calculate_reviewer_result_from_indicators(
            indicator_reviews
        )

    if reviewer_result is not None:
        reviewer_score = reviewer_result["reviewer_score"]
        reviewer_percentage = reviewer_result["reviewer_percentage"]

    elif submitted_standard_score is not None:
        reviewer_score = submitted_standard_score
        reviewer_percentage = percentage_from_score(
            reviewer_score
        )

    else:
        reviewer_score = None
        reviewer_percentage = None

    standard_review.reviewer_score = reviewer_score
    standard_review.reviewer_percentage = reviewer_percentage

    if reviewer_percentage is not None:
        standard_review.reviewer_weighted_score = decimal_round(
            (reviewer_percentage / Decimal("100"))
            * to_decimal(standard_review.weight)
        )
    else:
        standard_review.reviewer_weighted_score = None

    standard_review.modified_by_reviewer = (
        indicator_score_modified
        or (
            reviewer_score is not None
            and reviewer_score != standard_review.auto_score
        )
    )

    standard_review.save()

    return standard_review


@transaction.atomic
def save_standard_reviewer_review(
    request,
    review,
    standard_review_id,
    action="draft",
):
    """
    حفظ معيار واحد كمسودة أو اعتماده.

    review:
        كائن ProgramEvaluationReview.

    standard_review_id:
        رقم كائن StandardEvaluationReview المطلوب حفظه.
    """

    user = current_user_or_none(request)

    # العلاقة الصحيحة هي standard_reviews بالجمع
    standard_review = (
        review.standard_reviews
        .prefetch_related("indicator_reviews")
        .get(pk=standard_review_id)
    )

    # حفظ درجة المراجع والملاحظات وخطة التحسين والمؤشرات
    apply_standard_post_data(
        request=request,
        standard_review=standard_review,
    )

    # اعتماد المعيار
    if action == "approve":
        standard_review.review_status = "reviewed"
        standard_review.reviewed_by = user
        standard_review.reviewed_at = timezone.now()

        if user:
            standard_review.saved_by = user

    # حفظه كمسودة
    else:
        if standard_has_reviewer_input(standard_review):
            standard_review.review_status = "draft"
        else:
            standard_review.review_status = "empty"

        standard_review.reviewed_by = None
        standard_review.reviewed_at = None

        if user:
            standard_review.saved_by = user

    standard_review.save()

    # حفظ الملاحظات العامة إن أُرسلت
    if "general_notes" in request.POST:
        review.general_notes = clean_text(
            request.POST.get("general_notes", "")
        )

        review.save(
            update_fields=[
                "general_notes",
                "updated_at",
            ]
        )

    # إعادة حساب النسب والحالة النهائية
    recalculate_review_totals(review)
    refresh_program_review_status(review)

    return standard_review


# ============================================================
# توافق احتياطي مع الاسم القديم
# لا نستخدمه في الصفحة الجديدة إلا إذا لم يتم إرسال standard_review_id
# ============================================================

def post_has_meaningful_standard_input(request, standard_review):
    field_names = [
        f"standard_score_{standard_review.id}",
        f"standard_notes_{standard_review.id}",
        f"strengths_{standard_review.id}",
        f"weaknesses_{standard_review.id}",
        f"improvement_plan_{standard_review.id}",
        f"execution_time_{standard_review.id}",
    ]

    for field_name in field_names:
        if value_has_content(request.POST.get(field_name)):
            return True

    for indicator_review in standard_review.indicator_reviews.all():
        if value_has_content(request.POST.get(f"indicator_score_{indicator_review.id}")):
            return True

        if value_has_content(request.POST.get(f"indicator_notes_{indicator_review.id}")):
            return True

    return False


@transaction.atomic
def save_reviewer_review(request, review):
    action = clean_text(request.POST.get("action"))
    standard_review_id = clean_text(
        request.POST.get("standard_review_id")
        or request.POST.get("active_standard_id")
    )

    if standard_review_id:
        return save_standard_reviewer_review(
            request=request,
            review=review,
            standard_review_id=standard_review_id,
            action=action,
        )

    standard_reviews = (
        review.standard_reviews
        .prefetch_related("indicator_reviews")
        .all()
    )

    saved_standard = None

    for standard_review in standard_reviews:
        if not post_has_meaningful_standard_input(request, standard_review):
            continue

        saved_standard = save_standard_reviewer_review(
            request=request,
            review=review,
            standard_review_id=standard_review.id,
            action=action,
        )

    if "general_notes" in request.POST:
        review.general_notes = clean_text(request.POST.get("general_notes"))
        review.save(update_fields=["general_notes", "updated_at"])

    recalculate_review_totals(review)
    refresh_program_review_status(review)

    return saved_standard or review


# ============================================================
# تجهيز البيانات للعرض
# ============================================================

def build_review_context(
    review,
    only_status=None,
    only_reviewer_filled=False,
    standard_review_id=None,
):
    review = sync_review_weights(review)

    blocks = []
    standard_reviews = (
    review.standard_reviews
    .select_related(
        "standard",
        "saved_by",
        "reviewed_by",
    )
    .prefetch_related(
        "indicator_reviews"
    )
    .filter(
        standard__is_active=True
    )
    .order_by(
        "standard__number"
    )
)

    if only_status:
        standard_reviews = standard_reviews.filter(review_status=only_status)

    if standard_review_id:
        standard_reviews = standard_reviews.filter(id=standard_review_id)

    for standard_review in standard_reviews:
        has_input = standard_has_reviewer_input(standard_review)

        if only_reviewer_filled and not has_input:
            continue

        final_score = standard_review.reviewer_score or standard_review.auto_score
        final_percentage = standard_review.reviewer_percentage or standard_review.auto_percentage
        final_weighted = standard_review.reviewer_weighted_score or standard_review.auto_weighted_score

        indicators = []
        filled_indicators = []

        for indicator in standard_review.indicator_reviews.all():
            indicator_has_input = indicator_has_reviewer_input(indicator)
            indicator_final_score = indicator.reviewer_score or indicator.auto_score

            indicator_data = {
                "obj": indicator,
                "final_score": indicator_final_score,
                "label": score_label(indicator_final_score),
                "has_reviewer_input": indicator_has_input,
            }

            indicators.append(indicator_data)

            if indicator_has_input:
                filled_indicators.append(indicator_data)

        blocks.append({
            "obj": standard_review,
            "final_score": final_score,
            "final_percentage": final_percentage,
            "final_weighted": final_weighted,
            "final_label": score_label(final_score),
            "indicators": indicators,
            "filled_indicators": filled_indicators,
            "has_reviewer_input": has_input,
            "review_status": standard_review.review_status,
            "review_status_label": standard_status_label(standard_review.review_status),
            "is_empty": standard_review.review_status == "empty",
            "is_draft": standard_review.review_status == "draft",
            "is_reviewed": standard_review.review_status == "reviewed",
        })

    return blocks
