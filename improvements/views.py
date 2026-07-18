from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from dashboard.models import EvaluationFile
from evaluations.models import ProgramEvaluationReview, StandardEvaluationReview

from .models import ImprovementPlan


def _clean(value):
    return str(value or "").strip()


def _date_or_none(value):
    value = _clean(value)
    return value or None


def _normalize_percentage(value):
    if value is None or value == "":
        return Decimal("0.00")

    try:
        return Decimal(str(value)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _safe_percentage(value):
    return float(_normalize_percentage(value))


def _final_percentage(standard_review):
    """
    نستخدم نسبة المراجع فقط عند وجود درجة مراجعة فعلية،
    وإلا نعتمد النسبة الآلية.
    """
    if standard_review.reviewer_score is not None:
        return _normalize_percentage(
            standard_review.reviewer_percentage
        )

    return _normalize_percentage(
        standard_review.auto_percentage
    )


def _priority_from_standard(standard_review):
    percentage = _safe_percentage(
        _final_percentage(standard_review)
    )

    if standard_review.review_status == "empty":
        return "high"

    if percentage < 50:
        return "high"

    if percentage < 80:
        return "medium"

    return "low"


def _priority_label(priority):
    labels = {
        "high": "عالية",
        "medium": "متوسطة",
        "low": "منخفضة",
    }
    return labels.get(priority, "متوسطة")


def _build_gap_description(standard_review, percentage=None):
    if percentage is None:
        percentage = _final_percentage(standard_review)
    else:
        percentage = _normalize_percentage(percentage)

    if standard_review.weaknesses:
        return standard_review.weaknesses

    if standard_review.review_status == "empty":
        return (
            "لم تكتمل مراجعة هذا المعيار بعد، "
            "ويحتاج إلى استكمال التقييم والأدلة."
        )

    if percentage >= Decimal("80"):
        return (
            f"نسبة المعيار الحالية {percentage:.2f}%، "
            "وقد أُدرج المعيار للمتابعة بسبب حالة المراجعة "
            "أو وجود إجراء تحسيني مرتبط به، وليس بسبب انخفاض النسبة."
        )

    return (
        f"نسبة المعيار الحالية {percentage:.2f}%، "
        "وهذا يشير إلى وجود فجوة تحتاج إلى إجراء تحسيني ومتابعة."
    )


def _build_improvement_action(standard_review):
    if standard_review.improvement_plan:
        return standard_review.improvement_plan

    return (
        "استكمال متطلبات المعيار، مراجعة البيانات والأدلة المرتبطة به، "
        "وتوثيق الإجراء التصحيحي قبل الاعتماد النهائي."
    )


def _build_success_indicator(standard_review):
    return (
        "ارتفاع نسبة تحقق المعيار، اكتمال الأدلة المطلوبة، واعتماد المعيار "
        "بعد مراجعة مسؤول الجودة."
    )


def _build_required_evidence(standard_review):
    return (
        "الأدلة والوثائق الداعمة المرتبطة بالمعيار، مثل النماذج، المحاضر، "
        "المرفقات، أو تقارير المتابعة."
    )


def _get_selected_file(request):
    file_id = request.GET.get("file_id")

    if file_id:
        return get_object_or_404(
            EvaluationFile.objects.select_related("program"),
            id=file_id,
        )

    latest_review = (
        ProgramEvaluationReview.objects
        .select_related(
            "evaluation_file",
            "evaluation_file__program",
        )
        .order_by("-updated_at")
        .first()
    )

    if latest_review:
        return latest_review.evaluation_file

    return (
        EvaluationFile.objects
        .select_related("program")
        .exclude(status="template_preview")
        .order_by("-updated_at")
        .first()
    )


def _build_opportunities(selected_file):
    if not selected_file:
        return []

    review = (
        ProgramEvaluationReview.objects
        .filter(evaluation_file=selected_file)
        .first()
    )

    if not review:
        return []

    existing_plan_map = {
        plan.standard_review_id: plan.id
        for plan in ImprovementPlan.objects.filter(
            evaluation_file=selected_file,
            standard_review__isnull=False,
        ).only("id", "standard_review_id")
    }

    standard_reviews = (
        StandardEvaluationReview.objects
        .filter(review=review)
        .select_related(
            "standard",
            "review",
            "review__evaluation_file",
        )
        .prefetch_related("indicator_reviews")
        .order_by("standard__number")
    )

    opportunities = []

    for standard_review in standard_reviews:
        percentage = _final_percentage(standard_review)
        percentage_value = _safe_percentage(percentage)
        priority = _priority_from_standard(standard_review)

        should_suggest = (
            standard_review.review_status != "reviewed"
            or percentage_value < 80
            or bool(standard_review.weaknesses)
            or bool(standard_review.improvement_plan)
        )

        if not should_suggest:
            continue

        weak_indicators_count = 0

        for indicator in standard_review.indicator_reviews.all():
            if indicator.reviewer_score is not None:
                score = indicator.reviewer_score
            else:
                score = indicator.auto_score

            try:
                numeric_score = int(score or 1)
            except (TypeError, ValueError):
                numeric_score = 1

            if numeric_score <= 2:
                weak_indicators_count += 1

        plan_id = existing_plan_map.get(standard_review.id)

        opportunities.append({
            "standard_review": standard_review,
            "standard_number": standard_review.standard.number,
            "standard_title": standard_review.standard.title,
            "percentage": percentage,
            "percentage_display": f"{percentage:.2f}",
            "priority": priority,
            "priority_label": _priority_label(priority),
            "gap_description": _build_gap_description(
                standard_review,
                percentage,
            ),
            "improvement_action": _build_improvement_action(
                standard_review
            ),
            "weak_indicators_count": weak_indicators_count,
            "has_plan": bool(plan_id),
            "plan_id": plan_id,
        })

    return opportunities


def _build_summary(plans):
    total = plans.count()
    proposed = plans.filter(status="proposed").count()
    in_progress = plans.filter(status="in_progress").count()
    completed = plans.filter(status="completed").count()
    high_priority = plans.filter(priority="high").count()

    overdue = 0

    for plan in plans:
        if plan.is_overdue:
            overdue += 1

    return {
        "total": total,
        "proposed": proposed,
        "in_progress": in_progress,
        "completed": completed,
        "high_priority": high_priority,
        "overdue": overdue,
    }


def improvement_plans_page(request):
    selected_file = _get_selected_file(request)
    selected_status = request.GET.get("status", "all")
    selected_priority = request.GET.get("priority", "all")
    edit_id = request.GET.get("edit_id")
    manual_mode = request.GET.get("add") == "manual"

    try:
        open_plan_id = int(request.GET.get("open_plan") or 0)
    except (TypeError, ValueError):
        open_plan_id = 0

    evaluation_files = (
        EvaluationFile.objects
        .select_related("program")
        .exclude(status="template_preview")
        .order_by("-updated_at")
    )

    plans = (
        ImprovementPlan.objects
        .select_related(
            "evaluation_file",
            "evaluation_file__program",
            "standard_review",
        )
        .all()
    )

    if selected_file:
        plans = plans.filter(evaluation_file=selected_file)

    if selected_status != "all":
        plans = plans.filter(status=selected_status)

    if selected_priority != "all":
        plans = plans.filter(priority=selected_priority)

    edit_plan = None

    if edit_id:
        edit_plan = get_object_or_404(
            ImprovementPlan.objects.select_related(
                "evaluation_file",
                "evaluation_file__program",
                "standard_review",
            ),
            id=edit_id,
        )

        if selected_file and edit_plan.evaluation_file_id != selected_file.id:
            messages.error(
                request,
                "الخطة المحددة لا تتبع ملف التقييم الحالي.",
            )
            return redirect(
                f"{reverse('improvement_plans')}?file_id={selected_file.id}"
            )

    opportunities = _build_opportunities(selected_file)
    summary = _build_summary(plans)

    context = {
        "page_title": "خطط التحسين الأكاديمي",
        "evaluation_files": evaluation_files,
        "selected_file": selected_file,
        "selected_file_id": str(selected_file.id) if selected_file else "",
        "selected_status": selected_status,
        "selected_priority": selected_priority,
        "plans": plans,
        "opportunities": opportunities,
        "summary": summary,
        "edit_plan": edit_plan,
        "manual_mode": manual_mode,
        "open_plan_id": open_plan_id,
        "status_options": [
            ("all", "كل الحالات"),
            ("proposed", "مقترحة"),
            ("in_progress", "قيد التنفيذ"),
            ("completed", "مكتملة"),
            ("closed", "مغلقة"),
        ],
        "priority_options": [
            ("all", "كل الأولويات"),
            ("high", "عالية"),
            ("medium", "متوسطة"),
            ("low", "منخفضة"),
        ],
        "plan_status_choices": ImprovementPlan.STATUS_CHOICES,
        "plan_priority_choices": ImprovementPlan.PRIORITY_CHOICES,
    }

    return render(
        request,
        "improvements/improvement_plans.html",
        context,
    )


@require_POST
def create_plan_from_standard(request):
    standard_review_id = request.POST.get("standard_review_id")

    standard_review = get_object_or_404(
        StandardEvaluationReview.objects.select_related(
            "standard",
            "review",
            "review__evaluation_file",
        ),
        id=standard_review_id,
    )

    evaluation_file = standard_review.review.evaluation_file
    priority = _priority_from_standard(standard_review)
    percentage = _final_percentage(standard_review)

    plan, created = ImprovementPlan.objects.get_or_create(
        evaluation_file=evaluation_file,
        standard_review=standard_review,
        defaults={
            "standard_number": standard_review.standard.number,
            "standard_title": standard_review.standard.title,
            "title": f"تحسين {standard_review.standard.title}",
            "gap_description": _build_gap_description(
                standard_review,
                percentage,
            ),
            "improvement_action": _build_improvement_action(
                standard_review
            ),
            "responsible_party": "مسؤول البرنامج / وحدة الجودة",
            "priority": priority,
            "status": "proposed",
            "success_indicator": _build_success_indicator(
                standard_review
            ),
            "required_evidence": _build_required_evidence(
                standard_review
            ),
        },
    )

    if created:
        messages.success(
            request,
            "تم إنشاء خطة التحسين من نتيجة التحليل بنجاح.",
        )
    else:
        messages.warning(
            request,
            "توجد خطة تحسين محفوظة مسبقًا لهذا المعيار.",
        )

    return redirect(
        f"{reverse('improvement_plans')}"
        f"?file_id={evaluation_file.id}"
        f"&edit_id={plan.id}"
        f"#planEditForm"
    )


@require_POST
def create_manual_plan(request):
    evaluation_file_id = request.POST.get("evaluation_file_id")

    evaluation_file = get_object_or_404(
        EvaluationFile.objects.select_related("program"),
        id=evaluation_file_id,
    )

    valid_priorities = dict(ImprovementPlan.PRIORITY_CHOICES)
    valid_statuses = dict(ImprovementPlan.STATUS_CHOICES)

    priority = request.POST.get("priority", "medium")
    status = request.POST.get("status", "proposed")

    if priority not in valid_priorities:
        messages.error(request, "الأولوية المحددة غير صحيحة.")
        return redirect(
            f"{reverse('improvement_plans')}"
            f"?file_id={evaluation_file.id}"
            f"&add=manual"
            f"#manualPlanForm"
        )

    if status not in valid_statuses:
        messages.error(request, "حالة الخطة غير صحيحة.")
        return redirect(
            f"{reverse('improvement_plans')}"
            f"?file_id={evaluation_file.id}"
            f"&add=manual"
            f"#manualPlanForm"
        )

    title = _clean(request.POST.get("title"))
    improvement_action = _clean(
        request.POST.get("improvement_action")
    )

    if not title:
        messages.error(request, "عنوان الخطة مطلوب.")
        return redirect(
            f"{reverse('improvement_plans')}"
            f"?file_id={evaluation_file.id}"
            f"&add=manual"
            f"#manualPlanForm"
        )

    if not improvement_action:
        messages.error(request, "الإجراء التحسيني مطلوب.")
        return redirect(
            f"{reverse('improvement_plans')}"
            f"?file_id={evaluation_file.id}"
            f"&add=manual"
            f"#manualPlanForm"
        )

    ImprovementPlan.objects.create(
        evaluation_file=evaluation_file,
        standard_review=None,
        standard_number=None,
        standard_title="",
        title=title,
        gap_description=_clean(
            request.POST.get("gap_description")
        ),
        improvement_action=improvement_action,
        responsible_party=_clean(
            request.POST.get("responsible_party")
        ),
        priority=priority,
        status=status,
        start_date=_date_or_none(
            request.POST.get("start_date")
        ),
        due_date=_date_or_none(
            request.POST.get("due_date")
        ),
        success_indicator=_clean(
            request.POST.get("success_indicator")
        ),
        required_evidence=_clean(
            request.POST.get("required_evidence")
        ),
        notes=_clean(request.POST.get("notes")),
    )

    messages.success(
        request,
        "تمت إضافة خطة التحسين اليدوية بنجاح.",
    )

    return redirect(
        f"{reverse('improvement_plans')}"
        f"?file_id={evaluation_file.id}"
        f"#plansTable"
    )


@require_POST
def update_plan_status(request, plan_id):
    plan = get_object_or_404(
        ImprovementPlan,
        id=plan_id,
    )

    new_status = request.POST.get("status")
    valid_statuses = dict(ImprovementPlan.STATUS_CHOICES)

    if new_status not in valid_statuses:
        messages.error(request, "حالة الخطة غير صحيحة.")
        return redirect("improvement_plans")

    plan.status = new_status
    plan.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    messages.success(
        request,
        "تم تحديث حالة خطة التحسين.",
    )

    return redirect(
        f"{reverse('improvement_plans')}"
        f"?file_id={plan.evaluation_file.id}"
        f"#plansTable"
    )


@require_POST
def update_plan_details(request, plan_id):
    plan = get_object_or_404(
        ImprovementPlan,
        id=plan_id,
    )

    valid_priorities = dict(ImprovementPlan.PRIORITY_CHOICES)
    valid_statuses = dict(ImprovementPlan.STATUS_CHOICES)

    priority = request.POST.get("priority", plan.priority)
    status = request.POST.get("status", plan.status)

    if priority not in valid_priorities:
        messages.error(request, "الأولوية المحددة غير صحيحة.")
        return redirect(
            f"{reverse('improvement_plans')}"
            f"?file_id={plan.evaluation_file.id}"
            f"&edit_id={plan.id}"
            f"#planEditForm"
        )

    if status not in valid_statuses:
        messages.error(request, "حالة الخطة غير صحيحة.")
        return redirect(
            f"{reverse('improvement_plans')}"
            f"?file_id={plan.evaluation_file.id}"
            f"&edit_id={plan.id}"
            f"#planEditForm"
        )

    title = _clean(request.POST.get("title"))
    improvement_action = _clean(
        request.POST.get("improvement_action")
    )

    if not title:
        messages.error(request, "عنوان الخطة مطلوب.")
        return redirect(
            f"{reverse('improvement_plans')}"
            f"?file_id={plan.evaluation_file.id}"
            f"&edit_id={plan.id}"
            f"#planEditForm"
        )

    if not improvement_action:
        messages.error(request, "الإجراء التحسيني مطلوب.")
        return redirect(
            f"{reverse('improvement_plans')}"
            f"?file_id={plan.evaluation_file.id}"
            f"&edit_id={plan.id}"
            f"#planEditForm"
        )

    plan.title = title
    plan.gap_description = _clean(
        request.POST.get("gap_description")
    )
    plan.improvement_action = improvement_action
    plan.responsible_party = _clean(
        request.POST.get("responsible_party")
    )
    plan.priority = priority
    plan.status = status
    plan.start_date = _date_or_none(
        request.POST.get("start_date")
    )
    plan.due_date = _date_or_none(
        request.POST.get("due_date")
    )
    plan.success_indicator = _clean(
        request.POST.get("success_indicator")
    )
    plan.required_evidence = _clean(
        request.POST.get("required_evidence")
    )
    plan.notes = _clean(request.POST.get("notes"))

    plan.save()

    messages.success(
        request,
        "تم حفظ تفاصيل خطة التحسين بنجاح.",
    )

    return redirect(
        f"{reverse('improvement_plans')}"
        f"?file_id={plan.evaluation_file.id}"
        f"#plansTable"
    )
