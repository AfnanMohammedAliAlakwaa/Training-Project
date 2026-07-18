from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from dashboard.models import EvaluationFile

from .analysis_service import build_analysis_context
from .evaluation_service import (
    build_review_context,
    generate_auto_review,
    save_standard_reviewer_review,
)
from .models import (
    ProgramEvaluationReview,
    StandardEvaluationReview,
)


# ============================================================
# Helpers
# ============================================================

def _current_user_or_none(request):
    """
    إرجاع المستخدم الحالي عند تسجيل الدخول،
    وإرجاع None عندما لا يوجد مستخدم مسجل.
    """

    if hasattr(request, "user") and request.user.is_authenticated:
        return request.user

    return None


def _safe_int(value):
    """
    تحويل القيمة إلى رقم صحيح دون التسبب بخطأ.
    """

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_standard_cards(
    status,
    review=None,
    all_programs=False,
):
    """
    بناء بطاقات المعايير حسب الحالة.

    عند اختيار جميع البرامج:
    - تعرض المعايير التابعة لكل ملفات البرامج.

    عند اختيار ملف محدد:
    - تعرض المعايير التابعة لذلك الملف فقط.
    """

    cards = []

    standard_reviews = (
        StandardEvaluationReview.objects
        .filter(review_status=status)
        .exclude(
            review__evaluation_file__status="template_preview"
        )
        .select_related(
            "review",
            "review__evaluation_file",
            "review__evaluation_file__program",
            "standard",
            "saved_by",
            "reviewed_by",
        )
        .prefetch_related("indicator_reviews")
        .order_by("-updated_at")
    )

    # عند اختيار ملف محدد، نعرض معايير هذا الملف فقط.
    if not all_programs:
        if review is None:
            return []

        standard_reviews = standard_reviews.filter(
            review=review
        )

    for standard_review in standard_reviews:
        blocks = build_review_context(
            standard_review.review,
            standard_review_id=standard_review.id,
        )

        if not blocks:
            continue

        cards.append({
            "review": standard_review.review,
            "standard_review": standard_review,
            "block": blocks[0],
        })

    return cards


def _build_redirect_url(
    file_id,
    standard_review_id=None,
    extra_query=None,
    anchor="reviewForm",
):
    """
    بناء رابط إعادة التوجيه مع المحافظة على الملف والمعيار المختارين.
    """

    query_parts = [
        f"file_id={file_id}",
    ]

    if standard_review_id:
        query_parts.append(
            f"standard_review_id={standard_review_id}"
        )

    if extra_query:
        query_parts.extend(extra_query)

    url = f"{reverse('evaluation')}?{'&'.join(query_parts)}"

    if anchor:
        url += f"#{anchor}"

    return url


# ============================================================
# Evaluation Page
# ============================================================

def evaluation_page(request):
    file_id = (
        request.GET.get("file_id")
        or request.POST.get("file_id")
    )

    # عند فتح الصفحة لأول مرة يكون الاختيار الافتراضي:
    # جميع البرامج.
    if not file_id:
        file_id = "all"

    is_all_programs = (
        str(file_id).strip().lower() == "all"
    )

    active_standard_id = (
        request.GET.get("standard_review_id")
        or request.POST.get("standard_review_id")
        or request.POST.get("active_standard_id")
    )

    active_standard_id = _safe_int(
        active_standard_id
    )

    load_draft = (
        request.GET.get("load_draft") == "1"
    )

    evaluation_files = (
        EvaluationFile.objects
        .select_related("program")
        .exclude(status="template_preview")
        .annotate(
            saved_standards_count=Count(
                "standard_entries"
            )
        )
        .order_by("-updated_at")
    )

    selected_file = None
    review = None
    selected_standard_review = None
    review_blocks = []

    # ========================================================
    # تحميل ملف محدد فقط
    # ========================================================

    if file_id and not is_all_programs:
        selected_file = get_object_or_404(
            EvaluationFile.objects.select_related(
                "program"
            ),
            id=file_id,
        )

        existing_review = (
            ProgramEvaluationReview.objects
            .filter(
                evaluation_file=selected_file
            )
            .first()
        )

        # ====================================================
        # استقبال عمليات الحفظ والتوليد
        # ====================================================

        if request.method == "POST":
            action = request.POST.get("action")

            # إعادة توليد التقييم الآلي.
            if action == "generate":
                review = generate_auto_review(
                    selected_file,
                    _current_user_or_none(request),
                )

                messages.success(
                    request,
                    "تم توليد التقييم الآلي بنجاح.",
                )

                return redirect(
                    _build_redirect_url(
                        file_id=selected_file.id,
                        anchor=None,
                    )
                )

            review = existing_review

            # إنشاء التقييم تلقائيًا إذا لم يكن موجودًا.
            if not review:
                review = generate_auto_review(
                    selected_file,
                    _current_user_or_none(request),
                )

            standard_review_id = (
                request.POST.get(
                    "standard_review_id"
                )
                or request.POST.get(
                    "active_standard_id"
                )
            )

            standard_review_id = _safe_int(
                standard_review_id
            )

            if not standard_review_id:
                messages.error(
                    request,
                    (
                        "لم يتم تحديد المعيار المطلوب حفظه. "
                        "افتحي المعيار المطلوب ثم اضغطي "
                        "حفظ كمسودة أو اعتماد."
                    ),
                )

                return redirect(
                    _build_redirect_url(
                        file_id=selected_file.id,
                        anchor="reviewForm",
                    )
                )

            standard_review = (
                review.standard_reviews
                .select_related("standard")
                .filter(
                    id=standard_review_id
                )
                .first()
            )

            if not standard_review:
                messages.error(
                    request,
                    (
                        "المعيار المحدد غير موجود ضمن "
                        "ملف التقييم الحالي."
                    ),
                )

                return redirect(
                    _build_redirect_url(
                        file_id=selected_file.id,
                        anchor="reviewForm",
                    )
                )

            # منع تعديل المعيار المعتمد مباشرة.
            if standard_review.review_status == "reviewed":
                messages.error(
                    request,
                    (
                        "هذا المعيار معتمد بالفعل "
                        "ولا يمكن تعديله مباشرة."
                    ),
                )

                return redirect(
                    _build_redirect_url(
                        file_id=selected_file.id,
                        standard_review_id=(
                            standard_review.id
                        ),
                        extra_query=[
                            "approved_open=1"
                        ],
                        anchor=(
                            f"standard-card-"
                            f"{standard_review.id}"
                        ),
                    )
                )

            # =================================================
            # اعتماد المعيار
            # =================================================

            if action == "approve":
                saved_standard = (
                    save_standard_reviewer_review(
                        request=request,
                        review=review,
                        standard_review_id=(
                            standard_review.id
                        ),
                        action="approve",
                    )
                )

                messages.success(
                    request,
                    (
                        f"تم اعتماد "
                        f"{saved_standard.standard} "
                        f"بنجاح."
                    ),
                )

                return redirect(
                    _build_redirect_url(
                        file_id=selected_file.id,
                        standard_review_id=(
                            saved_standard.id
                        ),
                        extra_query=[
                            "approved_open=1"
                        ],
                        anchor=(
                            f"standard-card-"
                            f"{saved_standard.id}"
                        ),
                    )
                )

            # =================================================
            # حفظ المعيار كمسودة
            # =================================================

            saved_standard = (
                save_standard_reviewer_review(
                    request=request,
                    review=review,
                    standard_review_id=(
                        standard_review.id
                    ),
                    action="draft",
                )
            )

            if saved_standard.review_status == "empty":
                messages.warning(
                    request,
                    (
                        f"لم يتم حفظ "
                        f"{saved_standard.standard} "
                        f"كمسودة لأن حقوله فارغة."
                    ),
                )
            else:
                messages.success(
                    request,
                    (
                        f"تم حفظ "
                        f"{saved_standard.standard} "
                        f"كمسودة."
                    ),
                )

            return redirect(
                _build_redirect_url(
                    file_id=selected_file.id,
                    standard_review_id=(
                        saved_standard.id
                    ),
                    extra_query=[
                        "load_draft=1",
                        "draft_open=1",
                    ],
                    anchor="reviewForm",
                )
            )

        # ====================================================
        # تحميل التقييم المحفوظ للملف المختار
        # ====================================================

        # لا نعيد توليد التقييم عند كل فتح للصفحة؛
        # حتى تبقى حالات المعايير المعتمدة والمسودات محفوظة.
        # إعادة التوليد تتم فقط من زر "إعادة توليد التقييم الآلي".
        review = existing_review

        if not review:
            review = generate_auto_review(
                selected_file,
                _current_user_or_none(request),
            )

        if active_standard_id:
            selected_standard_review = (
                review.standard_reviews
                .select_related("standard")
                .filter(
                    id=active_standard_id
                )
                .first()
            )

            if selected_standard_review:
                review_blocks = build_review_context(
                    review,
                    standard_review_id=(
                        selected_standard_review.id
                    ),
                )
            else:
                review_blocks = build_review_context(
                    review
                )
        else:
            review_blocks = build_review_context(
                review
            )

    # ========================================================
    # المعايير المعتمدة والمسودات
    # ========================================================

    draft_standard_cards = _build_standard_cards(
        status="draft",
        review=review,
        all_programs=is_all_programs,
    )

    approved_standard_cards = _build_standard_cards(
        status="reviewed",
        review=review,
        all_programs=is_all_programs,
    )

    # ========================================================
    # Context
    # ========================================================

    context = {
        "page_title": "تقييم جودة البرنامج",

        # تحديد هل الاختيار الحالي جميع البرامج.
        "is_all_programs": is_all_programs,

        "evaluation_files": evaluation_files,
        "selected_file": selected_file,
        "review": review,

        "selected_standard_review": (
            selected_standard_review
        ),
        "active_standard_id": active_standard_id,
        "review_blocks": review_blocks,

        "draft_standard_cards": (
            draft_standard_cards
        ),
        "draft_open": (
            request.GET.get("draft_open") == "1"
        ),

        "approved_standard_cards": (
            approved_standard_cards
        ),
        "approved_open": (
            request.GET.get("approved_open") == "1"
        ),

        "load_draft": load_draft,

        "score_options": [
            (5, "5 - مستوفي بتميز"),
            (4, "4 - مستوفي بإتقان"),
            (3, "3 - مستوفي"),
            (2, "2 - مستوفي جزئيًا"),
            (1, "1 - غير مستوفي"),
        ],
    }

    return render(
        request,
        "evaluations/evaluation.html",
        context,
    )


# ============================================================
# Analysis Page
# ============================================================

def analysis_page(request):
    context = build_analysis_context(request)

    return render(
        request,
        "evaluations/analysis.html",
        context,
    )
