import json

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from programs.models import Program
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.forms import AuthenticationForm
from .program_catalog import get_program_options
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST
from programs.models import Program as MainProgram
from django.contrib.auth import login, logout
from evaluations.models import StandardEvaluationReview
from django.contrib.auth.decorators import login_not_required
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.contrib.auth.decorators import login_not_required
from .models import (
    AcademicProgram,
    CourseRecord,
    DataEntryTableRecord,
    EducationProcessRecord,
    EvaluationFile,
    EvidenceAttachment,
    FacultyMemberRecord,
    GraduateRecord,
    InfrastructureRecord,
    LibrarySourceRecord,
    QualityStandard,
    StandardEntry,
    StudentLevelCount,
    log_activity,
)
from .models import (
    AcademicProgram,
    CourseRecord,
    DataEntryTableRecord,
    EducationProcessRecord,
    EvaluationFile,
    EvidenceAttachment,
    FacultyMemberRecord,
    GraduateRecord,
    InfrastructureRecord,
    LibrarySourceRecord,
    QualityStandard,
    StandardEntry,
    StudentLevelCount,
    log_activity,
)


# ============================================================
# Unified Login Gateway
# ============================================================

@login_not_required
def login_gateway(request):
    return render(
        request,
        "dashboard/login_gateway.html",
    )


@login_not_required
@never_cache
def gateway_system_login(request):
    logout(request)

    return redirect("system_login")


@login_not_required
@never_cache
def gateway_admin_login(request):
    logout(request)

    return redirect("/admin/login/")
# ============================================================
# Constants
# ============================================================

COURSE_SPECIFICATION_TYPE = "course_specification"

# ============================================================
# Constants
# ============================================================

COURSE_SPECIFICATION_TYPE = "course_specification"

COURSE_REQUIREMENT_COLUMNS = [
    ("courses_university[]", "university_requirement"),
    ("courses_college[]", "college_requirement"),
    ("courses_department_required[]", "department_required_requirement"),
    ("courses_program_required[]", "program_required_requirement"),
    ("courses_program_optional[]", "program_optional_requirement"),
]

COURSE_REQUIREMENT_TO_FIELD = {
    "university_requirement": "courses_university[]",
    "college_requirement": "courses_college[]",
    "department_required_requirement": "courses_department_required[]",
    "program_required_requirement": "courses_program_required[]",
    "program_optional_requirement": "courses_program_optional[]",
}


# ============================================================
# Basic Helpers
# ============================================================

def clean_text(value):
    return str(value or "").strip()


def to_int(value, default=0):
    value = clean_text(value)

    if not value:
        return default

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def to_date_or_none(value):
    value = clean_text(value)

    if not value:
        return None

    return value


def date_to_input_value(value):
    if not value:
        return ""

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return clean_text(value)


def parse_weight(weight):
    value = clean_text(weight).replace("%", "")
    return to_int(value, 0)


def extract_year_number(value):
    value = clean_text(value)

    if not value:
        return None

    if "/" in value:
        value = value.split("/")[0]

    if "-" in value:
        value = value.split("-")[0]

    digits = "".join(ch for ch in value if ch.isdigit())

    if len(digits) < 4:
        return None

    return int(digits[:4])


def build_graduation_year_options(start_year_value, academic_year_value=None):
    start_year = extract_year_number(start_year_value)
    end_year = extract_year_number(academic_year_value)

    if not start_year:
        return []

    if not end_year or end_year < start_year:
        end_year = start_year + 9

    years = []

    for year in range(start_year, end_year + 1):
        years.append(f"{year}/{year + 1}")

    return years


def value_has_content(value):
    if value is None:
        return False

    if isinstance(value, dict):
        return any(value_has_content(item) for item in value.values())

    if isinstance(value, list):
        return any(value_has_content(item) for item in value)

    return bool(clean_text(value))


# ============================================================
# Standards Structure
# ============================================================

def get_data_entry_standards():
    return [
        {
            "id": "standard1",
            "tab_title": "1. معلومات البرنامج",
            "title": "المعيار الأول: معلومات البرنامج",
            "weight": "5%",
            "cards": [
                {
                    "title": "أولًا: معلومات عامة عن البرنامج",
                    "fields": [
                        {
                            "label": "اسم البرنامج",
                            "name": "program_name",
                            "type": "text",
                            "placeholder": "مثال: تقنية المعلومات",
                        },
                        {
                            "label": "نوع المؤهل",
                            "name": "qualification_type",
                            "type": "text",
                            "placeholder": "مثال: بكالوريوس",
                        },
                        {
                            "label": "نوع البرنامج",
                            "name": "program_type",
                            "type": "select",
                            "options": ["مستقل", "مشترك", "متعدد"],
                        },
                        {
                            "label": "نظام الدراسة",
                            "name": "study_system",
                            "type": "text",
                            "placeholder": "انتظام / ساعات معتمدة",
                        },
                        {
                            "label": "مدة البرنامج",
                            "name": "program_duration",
                            "type": "text",
                            "placeholder": "مثال: 4 سنوات",
                        },
                        {
                            "label": "تاريخ الحصول على الترخيص المبدئي",
                            "name": "initial_license_date",
                            "type": "date",
                        },
                        {
                            "label": "نوع الترخيص",
                            "name": "initial_license_type",
                            "type": "text",
                        },
                        {
                            "label": "رقم الهاتف",
                            "name": "program_phone",
                            "type": "text",
                        },
                        {
                            "label": "رقم الفاكس",
                            "name": "program_fax",
                            "type": "text",
                        },
                        {
                            "label": "موقع البرنامج في الإنترنت",
                            "name": "program_website",
                            "type": "url",
                            "placeholder": "https://example.com",
                        },
                        {
                            "label": "البريد الإلكتروني للبرنامج",
                            "name": "program_email",
                            "type": "email",
                        },
                        {
                            "label": "صندوق البريد",
                            "name": "postal_box",
                            "type": "text",
                        },
                        {
                            "label": "عنوان البرنامج",
                            "name": "program_address",
                            "type": "text",
                            "full": True,
                        },
                    ],
                },
                {
                    "title": "ثانيًا: معلومات عامة عن مسؤول البرنامج",
                    "fields": [
                        {
                            "label": "اسم مسؤول البرنامج",
                            "name": "manager_name",
                            "type": "text",
                        },
                        {
                            "label": "نوع الوظيفة",
                            "name": "manager_job_type",
                            "type": "text",
                        },
                        {
                            "label": "المؤهل العلمي",
                            "name": "manager_qualification",
                            "type": "text",
                        },
                        {
                            "label": "الدرجة / المرتبة الأكاديمية",
                            "name": "manager_rank",
                            "type": "text",
                        },
                        {
                            "label": "الجنسية",
                            "name": "manager_nationality",
                            "type": "text",
                        },
                        {
                            "label": "تاريخ التعيين في المؤسسة",
                            "name": "manager_appointment_date",
                            "type": "date",
                        },
                        {
                            "label": "جهة إصدار قرار التعيين",
                            "name": "appointment_authority",
                            "type": "text",
                        },
                        {
                            "label": "رقم قرار التعيين",
                            "name": "appointment_number",
                            "type": "text",
                        },
                        {
                            "label": "تاريخ قرار التعيين",
                            "name": "appointment_date",
                            "type": "date",
                        },
                        {
                            "label": "رقم الهاتف الشخصي",
                            "name": "manager_personal_phone",
                            "type": "text",
                        },
                        {
                            "label": "رقم هاتف المكتب",
                            "name": "manager_office_phone",
                            "type": "text",
                        },
                        {
                            "label": "التحويلة",
                            "name": "manager_extension",
                            "type": "text",
                        },
                        {
                            "label": "رقم الفاكس",
                            "name": "manager_fax",
                            "type": "text",
                        },
                        {
                            "label": "البريد الإلكتروني",
                            "name": "manager_email",
                            "type": "email",
                        },
                    ],
                },
                {
                    "title": "ثالثًا: نبذة عامة عن البرنامج",
                    "fields": [
                        {
                            "label": "نبذة عامة عن البرنامج",
                            "name": "program_overview",
                            "type": "textarea",
                            "full": True,
                        },
                        {
                            "label": "سنة إنشاء البرنامج",
                            "name": "program_establishment_year",
                            "type": "text",
                        },
                        {
                            "label": "اسم الكلية",
                            "name": "college_name",
                            "type": "text",
                        },
                        {
                            "label": "اسم القسم",
                            "name": "department_name",
                            "type": "text",
                        },
                        {
                            "label": "عدد أعضاء هيئة التدريس حملة الدكتوراه",
                            "name": "phd_faculty_count",
                            "type": "number",
                            
                        },
                        {
                            "label": "عدد المعامل / المختبرات",
                            "name": "labs_count",
                            "type": "number",
                        },
                        {
                            "label": "عدد الفنيين",
                            "name": "technicians_count",
                            "type": "number",
                        },
                        {
                            "label": "عدد الطلبة المقيدين حاليًا",
                            "name": "current_students_count",
                            "type": "number",
                        },
                        {
                            "label": "عدد الخريجين",
                            "name": "graduates_count",
                            "type": "number",
                        },
                    ],
                },
            ],
            "attachments": [
                {
                    "label": "ملحق 1: السيرة الذاتية لمسؤول البرنامج",
                    "name": "attachment_manager_cv",
                },
                {
                    "label": "ملحق 2: قرار تعيين مسؤول البرنامج",
                    "name": "attachment_manager_decision",
                },
                {
                    "label": "ملحق 3: معايير القبول والطاقة الاستيعابية",
                    "name": "attachment_admission_capacity",
                },
                {
                    "label": "ملحق 4: قائمة أعضاء هيئة التدريس ومساعديهم",
                    "name": "attachment_faculty_members",
                },
                {
                    "label": "ملحق 5: المعامل والورش والفنيين",
                    "name": "attachment_labs_technicians",
                },
                {
                    "label": "ملحق 6: أعداد الخريجين حسب السنوات",
                    "name": "attachment_graduates",
                },
                {
                    "label": "ملحق 7: أعداد الطلبة الملتحقين",
                    "name": "attachment_enrolled_students",
                },
            ],
        },
        {
            "id": "standard2",
            "tab_title": "2. الرسالة والأهداف",
            "title": "المعيار الثاني: رسالة وأهداف وخطط البرنامج",
            "weight": "10%",
            "cards": [
                {
                    "title": "رسالة البرنامج",
                    "fields": [
                        {
                            "label": "نص رسالة البرنامج",
                            "name": "program_mission",
                            "type": "textarea",
                            "full": True,
                        },
                    ],
                },
            ],
            "attachments": [
                {
                    "label": "ملحق 8: أدلة ورشة إعداد رسالة البرنامج ومحاضر الاعتماد",
                    "name": "attachment_mission_workshop",
                },
                {
                    "label": "ملحق 9: أدلة إعداد أهداف البرنامج ومحاضر الاعتماد",
                    "name": "attachment_goals_workshop",
                },
                {
                    "label": "ملحق 10: اتساق الرسالة والأهداف مع رسالة الكلية والجامعة",
                    "name": "attachment_mission_goals_alignment",
                },
                {
                    "label": "ملحق 11: الخطة التنفيذية للبرنامج",
                    "name": "attachment_executive_plan",
                },
            ],
        },
        {
            "id": "standard3",
            "tab_title": "3. مخرجات التعلم",
            "title": "المعيار الثالث: مخرجات تعلم البرنامج",
            "weight": "15%",
            "cards": [
                {
                    "title": "مخرجات التعلم حسب المجالات",
                    "fields": [
                        {
                            "label": "مهارات المعرفة والفهم",
                            "name": "knowledge_skills",
                            "type": "textarea",
                        },
                        {
                            "label": "المهارات الذهنية",
                            "name": "mental_skills",
                            "type": "textarea",
                        },
                        {
                            "label": "المهارات العملية / المهنية",
                            "name": "practical_skills",
                            "type": "textarea",
                        },
                        {
                            "label": "المهارات الحياتية / الانتقالية",
                            "name": "life_skills",
                            "type": "textarea",
                        },
                    ],
                    "two_columns": True,
                },
            ],
            "attachments": [
                {
                    "label": "ملحق 12: كشف دورات إعداد مواصفات المقررات",
                    "name": "attachment_course_spec_training",
                },
                {
                    "label": "ملحق 13: أدبيات ورشة إعداد وثيقة توصيف البرنامج",
                    "name": "attachment_program_spec_workshop",
                },
                {
                    "label": "ملحق 14: أدلة قياس مخرجات التعلم ورضا سوق العمل",
                    "name": "attachment_learning_outcomes_measurement",
                },
            ],
        },
        {
            "id": "standard4",
            "tab_title": "4. مواصفات البرنامج",
            "title": "المعيار الرابع: مواصفات البرنامج الأكاديمي",
            "weight": "15%",
            "cards": [
                {
                    "title": "وثيقة توصيف البرنامج والخطة الدراسية",
                    "fields": [
                        {
                            "label": "هل توجد وثيقة توصيف PSD؟",
                            "name": "has_psd",
                            "type": "select",
                            "options": ["نعم", "لا"],
                        },
                        {
                            "label": "إجمالي الساعات المعتمدة",
                            "name": "total_credit_hours",
                            "type": "number",
                        },
                        {
                            "label": "ساعات متطلبات الجامعة",
                            "name": "university_requirements_hours",
                            "type": "number",
                        },
                        {
                            "label": "نسبة متطلبات الجامعة",
                            "name": "university_requirements_percentage",
                            "type": "text",
                            "placeholder": "%",
                        },
                        {
                            "label": "ساعات متطلبات الكلية",
                            "name": "college_requirements_hours",
                            "type": "number",
                        },
                        {
                            "label": "نسبة متطلبات الكلية",
                            "name": "college_requirements_percentage",
                            "type": "text",
                            "placeholder": "%",
                        },
                        {
                            "label": "ساعات متطلبات القسم",
                            "name": "department_requirements_hours",
                            "type": "number",
                        },
                        {
                            "label": "نسبة متطلبات القسم",
                            "name": "department_requirements_percentage",
                            "type": "text",
                            "placeholder": "%",
                        },
                        {
                            "label": "ساعات متطلبات التخصص الإجبارية",
                            "name": "major_required_hours",
                            "type": "number",
                        },
                        {
                            "label": "نسبة متطلبات التخصص الإجبارية",
                            "name": "major_required_percentage",
                            "type": "text",
                            "placeholder": "%",
                        },
                        {
                            "label": "ساعات متطلبات التخصص الاختيارية",
                            "name": "major_optional_hours",
                            "type": "number",
                        },
                        {
                            "label": "نسبة متطلبات التخصص الاختيارية",
                            "name": "major_optional_percentage",
                            "type": "text",
                            "placeholder": "%",
                        },
                    ],
                },
            ],
            "attachments": [
                {
                    "label": "ملحق 15: وثيقة وصف البرنامج PSD",
                    "name": "attachment_psd",
                },
                {
                    "label": "ملحق 16: الخطة الدراسية للبرنامج",
                    "name": "attachment_study_plan",
                },
                {
                    "label": "ملحق 17: ساعات المتفرغين وغير المتفرغين",
                    "name": "attachment_full_part_time_hours",
                },
                {
                    "label": "ملحق 18: ساعات أعضاء هيئة التدريس من حملة الدكتوراه",
                    "name": "attachment_phd_teaching_hours",
                },
            ],
        },
        {
            "id": "standard5",
            "tab_title": "5. الطلبة",
            "title": "المعيار الخامس: الطلبة",
            "weight": "10%",
            "cards": [],
            "attachments": [
                {
                    "label": "كشف أعداد الطلبة حسب المستويات",
                    "name": "attachment_students_by_level",
                },
                {
                    "label": "كشف معدلات الأداء الأكاديمي للطلبة",
                    "name": "attachment_students_performance",
                },
                {
                    "label": "ملفات أو تقارير داعمة خاصة بالطلبة",
                    "name": "attachment_students_supporting_files",
                    "multiple": True,
                },
            ],
        },
        {
            "id": "standard6",
            "tab_title": "6. البنية المادية",
            "title": "المعيار السادس: البنية المادية للبرنامج",
            
            "attachments": [
                {
                    "label": "ملحق 19: قائمة القاعات الدراسية والمساحة والتجهيزات",
                    "name": "attachment_classrooms",
                },
                {
                    "label": "ملحق 20: قائمة المعامل والمختبرات والورش والتجهيزات",
                    "name": "attachment_labs_workshops",
                },
                {
                    "label": "ملفات داعمة للبنية المادية",
                    "name": "attachment_infrastructure_supporting_files",
                    "multiple": True,
                },
            ],
        },
        {
            "id": "standard7",
            "tab_title": "7. المكتبة",
            "title": "المعيار السابع: المكتبة",
            "weight": "10%",
            "cards": [
                {
                    "title": "مصادر المكتبة",
                    "fields": [
                        {
                            "label": "عدد الكتب المنهجية",
                            "name": "curriculum_books_count",
                            "type": "number",
                        },
                        {
                            "label": "عدد الكتب التخصصية",
                            "name": "specialized_books_count",
                            "type": "number",
                        },
                        {
                            "label": "عدد الدوريات والمراجع",
                            "name": "journals_references_count",
                            "type": "number",
                        },
                        {
                            "label": "عدد مصادر التعلم الإلكترونية",
                            "name": "digital_resources_count",
                            "type": "number",
                        },
                        {
                            "label": "عدد أجهزة الحاسوب في المكتبة",
                            "name": "library_computers_count",
                            "type": "number",
                        },
                        {
                            "label": "هل توجد حوسبة للمكتبة؟",
                            "name": "library_automation",
                            "type": "select",
                            "options": ["نعم", "لا"],
                        },
                        {
                            "label": "المساحة الإجمالية للمكتبة م²",
                            "name": "library_total_area",
                            "type": "number",
                        },
                        {
                            "label": "عدد المقاعد في المكتبة",
                            "name": "library_seats_count",
                            "type": "number",
                        },
                        {
                            "label": "مدى كفاية وحداثة مراجع البرنامج",
                            "name": "library_notes",
                            "type": "textarea",
                            "full": True,
                        },
                    ],
                },
            ],
            "attachments": [
                {
                    "label": "ملحق 21: قوائم الكتب المنهجية للتخصص",
                    "name": "attachment_curriculum_books",
                },
                {
                    "label": "ملحق 22: القوائم التخصصية التي تخدم البرنامج",
                    "name": "attachment_specialized_books",
                },
                {
                    "label": "ملحق 23: منهجية البحث عن المراجع",
                    "name": "attachment_reference_search_method",
                },
                {
                    "label": "ملحق 24: تجهيزات المكتبة",
                    "name": "attachment_library_equipment",
                },
                {
                    "label": "ملحق 25: قائمة أبحاث التخرج والرسائل العلمية",
                    "name": "attachment_research_projects",
                },
            ],
        },
        {
            "id": "standard8",
            "tab_title": "8. إدارة العملية التعليمية",
            "title": "المعيار الثامن: إدارة العملية التعليمية",
            "weight": "25%",
            "cards": [
                {
                    "title": "متابعة العملية التعليمية",
                    "fields": [
                        {
                            "label": "هل توجد تقارير سير محاضرات؟",
                            "name": "has_lecture_reports",
                            "type": "select",
                            "options": ["نعم", "لا"],
                        },
                        {
                            "label": "مطابقة الجداول للخطة الدراسية",
                            "name": "schedule_matches_plan",
                            "type": "select",
                            "options": ["مطابق", "مطابق جزئيًا", "غير مطابق"],
                        },
                        {
                            "label": "متابعة الساعات المكتبية",
                            "name": "office_hours_followup",
                            "type": "select",
                            "options": ["نعم", "لا"],
                        },
                        {
                            "label": "متابعة الأنشطة والتكاليف",
                            "name": "activities_assignments_followup",
                            "type": "select",
                            "options": ["نعم", "لا"],
                        },
                        {
                            "label": "تدريب ميداني / زيارات علمية / سمنارات",
                            "name": "field_training_activities",
                            "type": "select",
                            "options": ["نعم", "لا"],
                        },
                        {
                            "label": "مراجعة الورقة الامتحانية",
                            "name": "exam_paper_review",
                            "type": "select",
                            "options": ["نعم", "لا"],
                        },
                        {
                            "label": "رضا أعضاء هيئة التدريس",
                            "name": "faculty_satisfaction_rate",
                            "type": "text",
                            "placeholder": "%",
                        },
                        {
                            "label": "رضا الطلبة",
                            "name": "students_satisfaction_rate",
                            "type": "text",
                            "placeholder": "%",
                        },
                        {
                            "label": "تقييم سير العملية الامتحانية",
                            "name": "exam_process_evaluation_rate",
                            "type": "text",
                            "placeholder": "%",
                        },
                        {
                            "label": "وجود نظام إرشاد أكاديمي",
                            "name": "has_academic_guidance",
                            "type": "select",
                            "options": ["نعم", "لا"],
                        },
                        {
                            "label": "الإجراءات المتبعة في إدارة العملية التعليمية",
                            "name": "education_management_description",
                            "type": "textarea",
                            "full": True,
                        },
                    ],
                },
            ],
            "attachments": [
                {
                    "label": "ملحق 26: عدد الساعات ومطابقتها في الجداول الدراسية",
                    "name": "attachment_teaching_hours_schedule",
                },
                {
                    "label": "ملحق 27: متابعة الأنشطة الصفية والتكاليف والتدريب",
                    "name": "attachment_activities_training",
                },
                {
                    "label": "ملحق 28: مواضيع أبحاث التخرج ومتابعة التنفيذ",
                    "name": "attachment_graduation_research_topics",
                },
                {
                    "label": "ملحق 29: نتائج رضا أعضاء هيئة التدريس",
                    "name": "attachment_faculty_satisfaction",
                },
                {
                    "label": "ملحق 30: نتائج رضا الطلبة والخدمات المكتبية",
                    "name": "attachment_students_satisfaction",
                },
                {
                    "label": "ملحق 31: نظام الإرشاد والدعم الأكاديمي والنفسي",
                    "name": "attachment_academic_guidance",
                },
                {
                    "label": "ملحق 32: إجراءات تنمية وتطوير أعضاء هيئة التدريس",
                    "name": "attachment_staff_development",
                },
                {
                    "label": "ملحق 33: إجراءات ونتائج سير العملية الامتحانية",
                    "name": "attachment_exam_process",
                },
            ],
        },
    ]
def make_standard_tab_title(number, title):
    title = clean_text(title)

    if ":" in title:
        title = title.split(":", 1)[1].strip()

    if not title:
        title = f"المعيار {number}"

    return f"{number}. {title}"


def make_dynamic_standard_from_db(quality_standard):
    """
    يستخدم فقط إذا أضفتِ معيارًا جديدًا من الأدمن وليس له تصميم خاص داخل الصفحة.
    يظهر كمعيار عام بحقل نصي.
    """

    number = quality_standard.number

    return {
        "id": f"standard{number}",
        "number": number,
        "tab_title": make_standard_tab_title(number, quality_standard.title),
        "title": quality_standard.title,
        "weight": f"{quality_standard.weight}%",
        "cards": [
            {
                "title": "بيانات المعيار",
                "fields": [
                    {
                        "label": "تفاصيل المعيار",
                        "name": f"standard_{number}_notes",
                        "type": "textarea",
                        "full": True,
                        "placeholder": "اكتبي بيانات هذا المعيار هنا.",
                    },
                ],
            },
        ],
        "attachments": [],
    }


def get_data_entry_standards_from_admin():
    """
    هذه الدالة تجعل صفحة إدخال البيانات تقرأ عنوان المعيار والوزن النسبي
    من جدول QualityStandard في الأدمن.

    المهم:
    - لا نلغي التصميم التفصيلي الموجود للمعايير الثمانية.
    - فقط نستبدل العنوان والوزن من قاعدة البيانات.
    - إذا كان المعيار غير نشط في الأدمن، لا يظهر في صفحة الإدخال.
    - إذا أضيف معيار جديد في الأدمن، يظهر كمعيار عام بحقل نصي.
    """

    static_standards = get_data_entry_standards()

    db_standards = list(
        QualityStandard.objects.all().order_by("number")
    )

    db_by_number = {
        item.number: item
        for item in db_standards
    }

    final_standards = []
    static_numbers = set()

    for index, standard in enumerate(static_standards, start=1):
        standard_number = to_int(standard.get("number"), index)

        standard["number"] = standard_number
        static_numbers.add(standard_number)

        db_standard = db_by_number.get(standard_number)

        if db_standard:
            if not db_standard.is_active:
                continue

            standard["title"] = db_standard.title
            standard["weight"] = f"{db_standard.weight}%"
            standard["tab_title"] = make_standard_tab_title(
                db_standard.number,
                db_standard.title
            )

        final_standards.append(standard)

    for db_standard in db_standards:
        if not db_standard.is_active:
            continue

        if db_standard.number in static_numbers:
            continue

        final_standards.append(
            make_dynamic_standard_from_db(db_standard)
        )

    return sorted(
        final_standards,
        key=lambda item: to_int(item.get("number"), 9999)
    )    


@require_POST
def delete_evaluation_file(request, file_id):
    evaluation_file = get_object_or_404(
        EvaluationFile.objects.select_related("program"),
        id=file_id
    )

    program_name = str(evaluation_file.program)
    academic_year = evaluation_file.academic_year

    evaluation_file.delete()

    messages.success(
    request,
    f"تم حذف بيانات ملف التقييم: {program_name} / {academic_year}"
)

    return redirect("data_entry")
# ============================================================
# Program and Evaluation File
# ============================================================

# ============================================================
# Create New Evaluation File From Previous Template
# ============================================================

STATIC_STANDARD_NUMBERS_TO_COPY = [1, 2, 3, 4, 6, 7]

FORM_FIELDS_TO_CLEAR_WHEN_CLONING = [
    # بيانات تتغير سنويًا
    "current_students_count",
    "graduates_count",

    # مؤشرات أداء الطلبة
    "male_success_rate",
    "female_success_rate",
    "average_success_rate",
    "male_cumulative_gpa",
    "female_cumulative_gpa",
    "average_cumulative_gpa",
    "male_progress_rate",
    "female_progress_rate",
    "average_progress_rate",
    "male_retention_rate",
    "female_retention_rate",
    "average_retention_rate",
    "male_flow_rate",
    "female_flow_rate",
    "average_flow_rate",
    "male_withdrawal_rate",
    "female_withdrawal_rate",
    "average_withdrawal_rate",
]

DYNAMIC_TABLES_TO_COPY_AS_STATIC = [
    # المعيار السادس
    "classroomsDataTable",
    "labsDataTable",

    # المعيار السابع
    # جدول libraryCriteriaTable محسوب تلقائيًا، لذلك لا ننسخه كبيانات ثابتة.
    "librarySourcesTable",
]

DYNAMIC_TABLES_TO_NEVER_COPY = [
    # الطلاب والخريجون
    "studentsLevelsTable",
    "graduatesTable",

    # جدول محسوب تلقائيًا، لا يُنسخ ولا يُستعاد كصفوف ثابتة
    "libraryCriteriaTable",

    # ملحقات إدارة العملية التعليمية لأنها غالبًا سنوية
    "std8Annex26Table",
    "std8Annex27Table",
    "std8Annex28Table",
    "std8Annex29Table",
    "std8Annex30EducationTable",
    "std8Annex30LibraryTable",
    "std8Annex33Table",
]


def copy_standard_entries_as_template(source_file, target_file, new_program_name):
    source_entries = (
        StandardEntry.objects
        .filter(
            evaluation_file=source_file,
            standard__number__in=STATIC_STANDARD_NUMBERS_TO_COPY
        )
        .select_related("standard")
    )

    for source_entry in source_entries:
        old_form_data = source_entry.form_data or {}

        if not isinstance(old_form_data, dict):
            old_form_data = {}

        new_form_data = dict(old_form_data)

        # اسم البرنامج الجديد بدل اسم البرنامج القديم
        if "program_name" in new_form_data:
            new_form_data["program_name"] = new_program_name

        # تفريغ الحقول السنوية المتغيرة
        for field_name in FORM_FIELDS_TO_CLEAR_WHEN_CLONING:
            if field_name in new_form_data:
                new_form_data[field_name] = ""

        completion_status, completion_percentage = calculate_completion_status(new_form_data)

        StandardEntry.objects.update_or_create(
            evaluation_file=target_file,
            standard=source_entry.standard,
            defaults={
                "form_data": new_form_data,
                "completion_status": completion_status,
                "completion_percentage": completion_percentage,
                "saved_as_draft": True,
            },
        )


def copy_static_course_records(source_file, target_file):
    for record in CourseRecord.objects.filter(evaluation_file=source_file):
        CourseRecord.objects.create(
            evaluation_file=target_file,
            course_name=record.course_name,
            course_code=record.course_code,
            credit_hours=record.credit_hours,
            level=record.level,
            requirement_type=record.requirement_type,
            has_specification=record.has_specification,
        )


def copy_static_infrastructure_records(source_file, target_file):
    for record in InfrastructureRecord.objects.filter(evaluation_file=source_file):
        InfrastructureRecord.objects.create(
            evaluation_file=target_file,
            facility_type=record.facility_type,
            count=record.count,
            area=record.area,
            equipment=record.equipment,
            notes=record.notes,
        )


def copy_static_library_records(source_file, target_file):
    for record in LibrarySourceRecord.objects.filter(evaluation_file=source_file):
        LibrarySourceRecord.objects.create(
            evaluation_file=target_file,
            source_type=record.source_type,
            title=record.title,
            count=record.count,
            release_year=record.release_year,
            notes=record.notes,
        )


def copy_static_dynamic_tables(source_file, target_file):
    records = DataEntryTableRecord.objects.filter(
        evaluation_file=source_file,
        table_key__in=DYNAMIC_TABLES_TO_COPY_AS_STATIC,
    )

    for record in records:
        if record.table_key in DYNAMIC_TABLES_TO_NEVER_COPY:
            continue

        DataEntryTableRecord.objects.update_or_create(
            evaluation_file=target_file,
            table_key=record.table_key,
            defaults={
                "standard_key": record.standard_key,
                "table_title": record.table_title,
                "rows": record.rows or [],
            },
        )


@require_POST
@transaction.atomic
def create_evaluation_from_template(request):
    source_file_id = clean_text(request.POST.get("source_file_id"))
    new_program_name = clean_text(request.POST.get("new_program_name"))
    new_specialty = clean_text(request.POST.get("new_specialty"))
    new_academic_year = clean_text(request.POST.get("new_academic_year"))
    new_start_year = to_int(request.POST.get("new_start_year"), None)
    program_updated = False

    if not source_file_id:
        messages.error(request, "اختاري الملف السابق الذي سيتم استخدامه كقالب.")
        return redirect("data_entry")

    if not new_program_name:
        messages.error(request, "اكتبي اسم البرنامج الجديد.")
        return redirect("data_entry")

    if not new_academic_year:
        messages.error(request, "اكتبي سنة التقييم الجديدة.")
        return redirect("data_entry")

    source_file = get_object_or_404(EvaluationFile, id=source_file_id)

    if new_specialty in ["لا يوجد", "غير محددة", "-"]:
        new_specialty = ""

    target_program = (
        AcademicProgram.objects
        .filter(
            name=new_program_name,
            specialization=new_specialty,
    )
        .order_by("id")
        .first()
)

    if target_program is None:
        target_program = AcademicProgram.objects.create(
            name=new_program_name,
            specialization=new_specialty,
            start_year=new_start_year,
            is_active=True,
    )

        program_updated = False

    if new_start_year and target_program.start_year != new_start_year:
        target_program.start_year = new_start_year
        program_updated = True

    if not target_program.is_active:
        target_program.is_active = True
        program_updated = True

    if program_updated:
        target_program.save()

    # مهم جدًا:
    # هذا السطر يجب أن يكون خارج if program_updated
    existing_file = find_existing_evaluation_file(
        new_program_name,
        new_specialty,
        new_academic_year,
    )

    if existing_file:
        messages.error(
            request,
            f"لا يمكن إنشاء الملف؛ لأنه موجود مسبقًا: {existing_file.program} - سنة التقييم: {new_academic_year}. اختاري سنة أخرى أو برنامجًا آخر."
        )
        return redirect("data_entry")

    target_file, created_file = EvaluationFile.objects.get_or_create(
        program=target_program,
        academic_year=new_academic_year,
        defaults={
            "status": "template_preview",
        },
    )

    if not created_file:
        messages.warning(
            request,
            "يوجد ملف محفوظ مسبقًا لنفس البرنامج والسنة، لذلك تم فتح الملف الموجود بدل إنشاء نسخة جديدة."
        )
        return redirect(f"{reverse('data_entry')}?file_id={target_file.id}")

    copy_standard_entries_as_template(
        source_file=source_file,
        target_file=target_file,
        new_program_name=new_program_name,
    )

    copy_static_course_records(source_file, target_file)
    copy_static_infrastructure_records(source_file, target_file)
    copy_static_library_records(source_file, target_file)
    copy_static_dynamic_tables(source_file, target_file)

    messages.success(
        request,
        "تم إنشاء ملف جديد من بيانات سابقة. تم نسخ البيانات الثابتة وترك البيانات السنوية فارغة."
    )

    return redirect(f"{reverse('data_entry')}?file_id={target_file.id}")

def get_or_create_program_from_request(request):
    program_name = clean_text(request.POST.get("selected_program"))
    specialization = clean_text(request.POST.get("selected_specialty"))
    start_year = to_int(request.POST.get("selected_start_year"), None)

    if specialization in ["لا يوجد", "غير محددة", "-"]:
        specialization = ""

    if not program_name:
        program_name = "برنامج غير محدد"

    # نستخدم أول سجل مطابق بدل get_or_create
    # لأن قاعدة البيانات قد تحتوي على سجلات برامج مكررة.
    program = (
        AcademicProgram.objects
        .filter(
            name=program_name,
            specialization=specialization,
        )
        .order_by("id")
        .first()
    )

    # إذا لم يوجد البرنامج ننشئه.
    if program is None:
        program = AcademicProgram.objects.create(
            name=program_name,
            specialization=specialization,
            start_year=start_year,
            is_active=True,
        )

        return program

    updated_fields = []

    if start_year and program.start_year != start_year:
        program.start_year = start_year
        updated_fields.append("start_year")

    if not program.is_active:
        program.is_active = True
        updated_fields.append("is_active")

    if updated_fields:
        program.save(update_fields=updated_fields)

    return program


def get_or_create_evaluation_file(request):
    evaluation_file_id = clean_text(request.POST.get("evaluation_file_id"))
    program = get_or_create_program_from_request(request)
    academic_year = clean_text(request.POST.get("selected_academic_year"))

    if not academic_year:
        academic_year = "غير محددة"

    if evaluation_file_id:
        evaluation_file = (
            EvaluationFile.objects
            .select_related("program")
            .filter(id=evaluation_file_id)
            .first()
        )

        if evaluation_file:
            updated = False
            if evaluation_file.status == "template_preview":
                evaluation_file.status = "in_progress"
                updated = True

            if evaluation_file.program_id != program.id:
                evaluation_file.program = program
                updated = True

            if evaluation_file.academic_year != academic_year:
                evaluation_file.academic_year = academic_year
                updated = True

            if updated:
                evaluation_file.save()

            return evaluation_file

    evaluation_file, created = EvaluationFile.objects.get_or_create(
        program=program,
        academic_year=academic_year,
        defaults={
            "status": "in_progress",
        },
    )

    return evaluation_file


# ============================================================
# Save Standard Entries
# ============================================================

def collect_admission_criteria_rows(request):
    criteria = request.POST.getlist("admission_criteria[]")
    rows = []

    for criterion in criteria:
        criterion = clean_text(criterion)

        if not criterion:
            continue

        rows.append({
            "admission_criteria[]": criterion,
        })

    return rows


def collect_program_goals_rows(request):
    goals = request.POST.getlist("program_goals[]")
    rows = []

    for goal in goals:
        goal = clean_text(goal)

        if not goal:
            continue

        rows.append({
            "program_goals[]": goal,
        })

    return rows


def collect_outcomes_preparation_rows(request):
    items = request.POST.getlist("outcomes_preparation[]")
    rows = []

    for item in items:
        item = clean_text(item)

        if not item:
            continue

        rows.append({
            "outcomes_preparation[]": item,
        })

    return rows


def collect_faculty_summary_data(request):
    field_names = [
        "fulltime_professor",
        "fulltime_associate_professor",
        "fulltime_assistant_professor",
        "fulltime_assistant_lecturer",
        "fulltime_research_assistant",
        "fulltime_faculty_total",
        "supporting_professor",
        "supporting_associate_professor",
        "supporting_assistant_professor",
        "supporting_assistant_lecturer",
        "supporting_research_assistant",
        "supporting_faculty_total",
    ]

    data = {}

    for field_name in field_names:
        data[field_name] = clean_text(request.POST.get(field_name))

    return data


def collect_standard4_teaching_hours_data(request):
    field_names = [
        "fulltime_teaching_hours",
        "parttime_teaching_hours",
        "fulltime_parttime_teaching_percentage",
        "phd_teaching_hours",
        "program_total_teaching_hours",
        "phd_teaching_hours_percentage",
    ]

    data = {}

    for field_name in field_names:
        data[field_name] = clean_text(request.POST.get(field_name))

    return data


def collect_student_performance_rates_data(request):
    field_names = [
        "male_success_rate",
        "female_success_rate",
        "average_success_rate",
        "male_cumulative_gpa",
        "female_cumulative_gpa",
        "average_cumulative_gpa",
        "male_progress_rate",
        "female_progress_rate",
        "average_progress_rate",
        "male_retention_rate",
        "female_retention_rate",
        "average_retention_rate",
        "male_flow_rate",
        "female_flow_rate",
        "average_flow_rate",
        "male_withdrawal_rate",
        "female_withdrawal_rate",
        "average_withdrawal_rate",
    ]

    data = {}

    for field_name in field_names:
        data[field_name] = clean_text(request.POST.get(field_name))

    return data

def collect_standard7_equipment_data(request):
    """
    يحفظ حقول تجهيزات المكتبة الجديدة الموجودة في HTML.
    هذه الحقول ليست كلها موجودة داخل cards في get_data_entry_standards،
    لذلك إذا لم نجمعها هنا فلن تُحفظ ولن تُسترجع عند فتح الملف.
    """

    field_names = [
        "library_total_area",
        "library_chairs_count",
        "library_staff_computers_count",
        "library_students_computers_count",
        "library_electronic_sources_count",
        "library_curriculum_books_count",
        "library_specialized_books_count",
        "library_has_automation",
        "library_staff_count",
        "library_specialist_staff_count",
        "library_university_students_total",
    ]

    data = {}

    for field_name in field_names:
        data[field_name] = clean_text(request.POST.get(field_name))

    return data
def collect_standard_form_data(request, standard):
    form_data = {}

    for card in standard.get("cards", []):
        for field in card.get("fields", []):
            field_name = field.get("name")

            if not field_name:
                continue

            form_data[field_name] = clean_text(request.POST.get(field_name))

    standard_id = standard.get("id")

    if standard_id == "standard1":
        form_data["admissionCriteriaTable"] = collect_admission_criteria_rows(request)
        form_data["admission_capacity"] = clean_text(request.POST.get("admission_capacity"))
        form_data.update(collect_faculty_summary_data(request))

    if standard_id == "standard2":
        form_data["programGoalsTable"] = collect_program_goals_rows(request)

    if standard_id == "standard3":
        form_data["outcomesPreparationTable"] = collect_outcomes_preparation_rows(request)

    if standard_id == "standard4":
        form_data.update(collect_standard4_teaching_hours_data(request))

    if standard_id == "standard5":
        form_data.update(collect_student_performance_rates_data(request))

    # مهم جدًا: حفظ حقول تجهيزات المكتبة المخصصة في المعيار السابع
    if standard_id == "standard7":
        form_data.update(collect_standard7_equipment_data(request))

    return form_data


def calculate_completion_status(form_data):
    values = list(form_data.values())

    if not values:
        return "empty", 0

    filled_count = len([value for value in values if value_has_content(value)])
    total_count = len(values)

    if filled_count == 0:
        return "empty", 0

    percentage = round((filled_count / total_count) * 100)

    if filled_count == total_count:
        return "complete", percentage

    return "partial", percentage


def save_standard_entries(request, evaluation_file, standards):
    save_mode = clean_text(request.POST.get("save_mode"))
    saved_as_draft = save_mode == "draft"

    for index, standard in enumerate(standards, start=1):
        standard_number = to_int(standard.get("number"), index)

        quality_standard, created = QualityStandard.objects.get_or_create(

            number=standard_number,

            defaults={
                "title": standard.get("title", ""),
                "weight": parse_weight(standard.get("weight", 0)),
                "is_active": True,
            },
        )

        form_data = collect_standard_form_data(request, standard)
        completion_status, completion_percentage = calculate_completion_status(form_data)

        standard_entry, created = StandardEntry.objects.update_or_create(
            evaluation_file=evaluation_file,
            standard=quality_standard,
            defaults={
                "form_data": form_data,
                "completion_status": completion_status,
                "completion_percentage": completion_percentage,
                "saved_as_draft": saved_as_draft,
            },
        )

        save_attachments(request, standard_entry, standard)


def save_attachments(request, standard_entry, standard):
    for attachment in standard.get("attachments", []):
        field_name = attachment.get("name")
        title = attachment.get("label", field_name)

        if not field_name:
            continue

        uploaded_files = request.FILES.getlist(field_name)

        if not uploaded_files:
            continue

        EvidenceAttachment.objects.filter(
            standard_entry=standard_entry,
            title=title,
        ).delete()

        for uploaded_file in uploaded_files:
            EvidenceAttachment.objects.create(
                standard_entry=standard_entry,
                title=title,
                file=uploaded_file,
            )


# ============================================================
# Save Tables
# ============================================================

def delete_old_table_records(evaluation_file):
    StudentLevelCount.objects.filter(evaluation_file=evaluation_file).delete()
    GraduateRecord.objects.filter(evaluation_file=evaluation_file).delete()
    CourseRecord.objects.filter(evaluation_file=evaluation_file).delete()
    FacultyMemberRecord.objects.filter(evaluation_file=evaluation_file).delete()
    InfrastructureRecord.objects.filter(evaluation_file=evaluation_file).delete()
    LibrarySourceRecord.objects.filter(evaluation_file=evaluation_file).delete()
    EducationProcessRecord.objects.filter(evaluation_file=evaluation_file).delete()


# ============================================================
# Dynamic Tables Fallback Maps
# ============================================================

# جداول عادية: كل صف يكرر نفس أسماء الحقول
DYNAMIC_TABLE_COLUMN_MAPS = {
    # ========================================================
    # المعيار السادس
    # ========================================================
    "classroomsDataTable": {
        "standard_key": "standard6",
        "table_title": "قائمة بالقاعات الدراسية والمساحة والتجهيزات",
        "fields": [
            "classroom_group[]",
            "classroom_name[]",
            "classroom_area[]",
            "classroom_capacity[]",
            "classroom_has_desk[]",
            "classroom_has_projector[]",
            "classroom_has_board[]",
            "classroom_has_platform[]",
        ],
    },
    "labsDataTable": {
        "standard_key": "standard6",
        "table_title": "قائمة بالمعامل والمختبرات والورش والمساحة والتجهيزات",
        "fields": [
            "lab_kind[]",
            "lab_name[]",
            "lab_area[]",
            "lab_capacity[]",
            "lab_devices_count[]",
            "lab_has_projector[]",
            "lab_has_board[]",
        ],
    },

    # ========================================================
    # المعيار الثامن - جداول قابلة لإضافة صفوف
    # ========================================================
    "std8Annex26Table": {
        "standard_key": "standard8",
        "table_title": "عدد الساعات للمقرر ومطابقتها في الجدول الدراسي وعدد المحاضرات المنفذة",
        "fields": [
            "std8_26_course[]",
            "std8_26_desc_hours[]",
            "std8_26_schedule_hours[]",
            "std8_26_done_lectures[]",
            "std8_26_office_hours_percent[]",
        ],
    },
    "std8Annex27Table": {
        "standard_key": "standard8",
        "table_title": "متابعة الأنشطة الصفية والتكاليف والتدريب",
        "fields": [
            "std8_27_course[]",
            "std8_27_class_activity[]",
            "std8_27_assignment_followup[]",
            "std8_27_practical_training[]",
            "std8_27_teacher_feedback[]",
        ],
    },
    "std8Annex28Table": {
        "standard_key": "standard8",
        "table_title": "قائمة بالمواضيع الجديدة للأبحاث المتعلقة بالتخصص ومتابعة تنفيذها",
        "fields": [
            "std8_28_new_topics[]",
            "std8_28_execution_followup[]",
        ],
    },
}


# جداول ثابتة: كل صف له أسماء حقول مختلفة
# وهنا كان سبب المشكلة؛ لا يجوز جمعها كصف واحد.
DYNAMIC_TABLE_ROW_MAPS = {
    "std8Annex29Table": {
        "standard_key": "standard8",
        "table_title": "نتائج رضا أعضاء هيئة التدريس",
        "rows": [
            ["std8_29_current_salary[]", "std8_29_previous_salary[]"],
            ["std8_29_current_training[]", "std8_29_previous_training[]"],
            ["std8_29_current_work_conditions[]", "std8_29_previous_work_conditions[]"],
            ["std8_29_current_management[]", "std8_29_previous_management[]"],
            ["std8_29_current_policies[]", "std8_29_previous_policies[]"],
            ["std8_29_current_services[]", "std8_29_previous_services[]"],
            ["std8_29_current_general_climate[]", "std8_29_previous_general_climate[]"],
        ],
    },
    "std8Annex30EducationTable": {
        "standard_key": "standard8",
        "table_title": "نتائج رضا الطلبة على جودة الخدمات التعليمية المقدمة لهم",
        "rows": [
            ["std8_30_edu_current_infrastructure[]", "std8_30_edu_previous_infrastructure[]"],
            ["std8_30_edu_current_staff[]", "std8_30_edu_previous_staff[]"],
            ["std8_30_edu_current_admission[]", "std8_30_edu_previous_admission[]"],
            ["std8_30_edu_current_public_services[]", "std8_30_edu_previous_public_services[]"],
            ["std8_30_edu_current_student_activities[]", "std8_30_edu_previous_student_activities[]"],
            ["std8_30_edu_current_university_image[]", "std8_30_edu_previous_university_image[]"],
            ["std8_30_edu_current_personal_development[]", "std8_30_edu_previous_personal_development[]"],
        ],
    },
    "std8Annex30LibraryTable": {
        "standard_key": "standard8",
        "table_title": "نتائج رضا الطلبة على جودة الخدمات المكتبية",
        "rows": [
            ["std8_30_lib_current_admin_services[]", "std8_30_lib_previous_admin_services[]"],
            ["std8_30_lib_current_learning_resources[]", "std8_30_lib_previous_learning_resources[]"],
            ["std8_30_lib_current_environment[]", "std8_30_lib_previous_environment[]"],
        ],
    },
    "std8Annex33Table": {
        "standard_key": "standard8",
        "table_title": "نتائج تقييم سير العملية الامتحانية",
        "rows": [
            ["std8_33_current_organization[]", "std8_33_previous_organization[]"],
            ["std8_33_current_equipment[]", "std8_33_previous_equipment[]"],
            ["std8_33_current_halls_readiness[]", "std8_33_previous_halls_readiness[]"],
            ["std8_33_current_forms_availability[]", "std8_33_previous_forms_availability[]"],
        ],
    },
}


def normalize_dynamic_cell_value(value):
    """
    تنظيف قيمة الخلية قبل حفظها داخل JSON.
    يدعم النصوص، الأرقام، القوائم، والقيم الفارغة.
    """
    if value is None:
        return ""

    if isinstance(value, list):
        return [
            clean_text(item)
            for item in value
            if clean_text(item)
        ]

    if isinstance(value, dict):
        return {
            clean_text(key): normalize_dynamic_cell_value(item)
            for key, item in value.items()
            if clean_text(key)
        }

    return clean_text(value)


def dynamic_row_has_value(row):
    """
    تتحقق هل الصف يحتوي على قيمة حقيقية أم لا.
    مهم حتى لا نحفظ الصفوف الفارغة.
    """
    if not isinstance(row, dict):
        return False

    for key, value in row.items():
        # نتجاهل رقم الصف لأنه ليس إدخالًا من المستخدم
        if key == "__row_index":
            continue

        if isinstance(value, list):
            if any(clean_text(item) for item in value):
                return True

        elif isinstance(value, dict):
            if dynamic_row_has_value(value):
                return True

        else:
            if clean_text(value):
                return True

    return False
# ============================================================
# Dynamic Tables POST Fallback
# ============================================================

DYNAMIC_TABLE_COLUMN_MAPS = {
    # المعيار السادس
    "classroomsDataTable": {
        "standard_key": "standard6",
        "table_title": "قائمة بالقاعات الدراسية والمساحة والتجهيزات",
        "fields": [
            "classroom_group[]",
            "classroom_name[]",
            "classroom_area[]",
            "classroom_capacity[]",
            "classroom_has_desk[]",
            "classroom_has_projector[]",
            "classroom_has_board[]",
            "classroom_has_platform[]",
        ],
    },
    "labsDataTable": {
        "standard_key": "standard6",
        "table_title": "قائمة بالمعامل والمختبرات والورش والمساحة والتجهيزات",
        "fields": [
            "lab_kind[]",
            "lab_name[]",
            "lab_area[]",
            "lab_capacity[]",
            "lab_devices_count[]",
            "lab_has_projector[]",
            "lab_has_board[]",
        ],
    },

    # المعيار الثامن - الجداول التي يمكن أن تتكرر صفوفها
    "std8Annex26Table": {
        "standard_key": "standard8",
        "table_title": "عدد الساعات ومطابقتها في الجداول الدراسية",
        "fields": [
            "std8_26_course[]",
            "std8_26_desc_hours[]",
            "std8_26_schedule_hours[]",
            "std8_26_done_lectures[]",
            "std8_26_office_hours_percent[]",
        ],
    },
    "std8Annex27Table": {
        "standard_key": "standard8",
        "table_title": "متابعة الأنشطة الصفية والتكاليف والتدريب",
        "fields": [
            "std8_27_course[]",
            "std8_27_class_activity[]",
            "std8_27_assignment_followup[]",
            "std8_27_practical_training[]",
            "std8_27_teacher_feedback[]",
        ],
    },
    "std8Annex28Table": {
        "standard_key": "standard8",
        "table_title": "مواضيع أبحاث التخرج ومتابعة التنفيذ",
        "fields": [
            "std8_28_new_topics[]",
            "std8_28_execution_followup[]",
        ],
    },
}


DYNAMIC_TABLE_ROW_MAPS = {
    # المعيار الثامن - جداول ثابتة، كل صف له حقول مختلفة

    "std8Annex29Table": {
        "standard_key": "standard8",
        "table_title": "نتائج رضا أعضاء هيئة التدريس",
        "rows": [
            ["std8_29_current_salary[]", "std8_29_previous_salary[]"],
            ["std8_29_current_training[]", "std8_29_previous_training[]"],
            ["std8_29_current_work_conditions[]", "std8_29_previous_work_conditions[]"],
            ["std8_29_current_management[]", "std8_29_previous_management[]"],
            ["std8_29_current_policies[]", "std8_29_previous_policies[]"],
            ["std8_29_current_services[]", "std8_29_previous_services[]"],
            ["std8_29_current_general_climate[]", "std8_29_previous_general_climate[]"],
        ],
    },

    "std8Annex30EducationTable": {
        "standard_key": "standard8",
        "table_title": "رضا الطلبة على جودة الخدمات التعليمية",
        "rows": [
            ["std8_30_edu_current_infrastructure[]", "std8_30_edu_previous_infrastructure[]"],
            ["std8_30_edu_current_staff[]", "std8_30_edu_previous_staff[]"],
            ["std8_30_edu_current_admission[]", "std8_30_edu_previous_admission[]"],
            ["std8_30_edu_current_public_services[]", "std8_30_edu_previous_public_services[]"],
            ["std8_30_edu_current_student_activities[]", "std8_30_edu_previous_student_activities[]"],
            ["std8_30_edu_current_university_image[]", "std8_30_edu_previous_university_image[]"],
            ["std8_30_edu_current_personal_development[]", "std8_30_edu_previous_personal_development[]"],
        ],
    },

    "std8Annex30LibraryTable": {
        "standard_key": "standard8",
        "table_title": "رضا الطلبة على جودة الخدمات المكتبية",
        "rows": [
            ["std8_30_lib_current_admin_services[]", "std8_30_lib_previous_admin_services[]"],
            ["std8_30_lib_current_learning_resources[]", "std8_30_lib_previous_learning_resources[]"],
            ["std8_30_lib_current_environment[]", "std8_30_lib_previous_environment[]"],
        ],
    },

    "std8Annex33Table": {
        "standard_key": "standard8",
        "table_title": "تقييم سير العملية الامتحانية",
        "rows": [
            ["std8_33_current_organization[]", "std8_33_previous_organization[]"],
            ["std8_33_current_equipment[]", "std8_33_previous_equipment[]"],
            ["std8_33_current_halls_readiness[]", "std8_33_previous_halls_readiness[]"],
            ["std8_33_current_forms_availability[]", "std8_33_previous_forms_availability[]"],
        ],
    },
}


def collect_dynamic_rows_from_post(request, field_names):
    columns = {
        field_name: request.POST.getlist(field_name)
        for field_name in field_names
    }

    max_rows = 0

    for values in columns.values():
        max_rows = max(max_rows, len(values))

    rows = []

    for index in range(max_rows):
        row = {
            "__row_index": index + 1
        }

        for field_name in field_names:
            values = columns.get(field_name, [])
            value = values[index] if index < len(values) else ""
            row[field_name] = clean_text(value)

        if dynamic_row_has_value(row):
            rows.append(row)

    return rows


def collect_fixed_dynamic_rows_from_post(request, row_field_groups):
    rows = []

    for index, field_names in enumerate(row_field_groups, start=1):
        row = {
            "__row_index": index
        }

        for field_name in field_names:
            values = request.POST.getlist(field_name)
            row[field_name] = clean_text(values[0] if values else "")

        if dynamic_row_has_value(row):
            rows.append(row)

    return rows


def build_dynamic_tables_payload_from_post(request):
    payload = {}

    for table_key, config in DYNAMIC_TABLE_COLUMN_MAPS.items():
        rows = collect_dynamic_rows_from_post(
            request,
            config.get("fields", [])
        )

        if rows:
            payload[table_key] = {
                "standard_key": config.get("standard_key", ""),
                "table_title": config.get("table_title", ""),
                "rows": rows,
            }

    for table_key, config in DYNAMIC_TABLE_ROW_MAPS.items():
        rows = collect_fixed_dynamic_rows_from_post(
            request,
            config.get("rows", [])
        )

        if rows:
            payload[table_key] = {
                "standard_key": config.get("standard_key", ""),
                "table_title": config.get("table_title", ""),
                "rows": rows,
            }

    return payload
def save_dynamic_tables(request, evaluation_file):
    raw_json = request.POST.get("dynamic_tables_json", "")

    print("RAW dynamic_tables_json length =", len(raw_json))
    print("RAW dynamic_tables_json start =", raw_json[:300])

    if not raw_json:
        print("لم يصل dynamic_tables_json إلى views.py")
        return

    try:
        tables_payload = json.loads(raw_json)
    except json.JSONDecodeError as error:
        print("JSON ERROR in dynamic_tables_json:", error)
        return

    if not isinstance(tables_payload, dict):
        print("dynamic_tables_json ليس dict")
        return

    print("TABLE KEYS RECEIVED =", list(tables_payload.keys()))

    DataEntryTableRecord.objects.filter(
        evaluation_file=evaluation_file
    ).delete()

    for table_key, table_data in tables_payload.items():
        table_key = clean_text(table_key)

        # جدول محسوب، لا نحفظه كمدخلات
        if table_key == "libraryCriteriaTable":
            continue

        if not table_key:
            continue

        if not isinstance(table_data, dict):
            continue

        standard_key = clean_text(table_data.get("standard_key", ""))
        table_title = clean_text(table_data.get("table_title", ""))
        rows = table_data.get("rows", [])

        if not isinstance(rows, list):
            continue

        cleaned_rows = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            cleaned_row = {}

            for key, value in row.items():
                cleaned_key = clean_text(key)

                if not cleaned_key:
                    continue

                cleaned_row[cleaned_key] = normalize_dynamic_cell_value(value)

            if dynamic_row_has_value(cleaned_row):
                cleaned_rows.append(cleaned_row)

        if not cleaned_rows:
            continue

        DataEntryTableRecord.objects.update_or_create(
            evaluation_file=evaluation_file,
            table_key=table_key,
            defaults={
                "standard_key": standard_key,
                "table_title": table_title,
                "rows": cleaned_rows,
            },
        )

        print("SAVED TABLE:", table_key, "ROWS:", len(cleaned_rows))
def save_student_level_counts(request, evaluation_file):
    levels = request.POST.getlist("student_level[]")
    males = request.POST.getlist("student_male[]")
    females = request.POST.getlist("student_female[]")

    for index, level in enumerate(levels):
        level = clean_text(level)

        raw_male = clean_text(males[index] if index < len(males) else "")
        raw_female = clean_text(females[index] if index < len(females) else "")

        if not raw_male and not raw_female:
            continue

        male_count = to_int(raw_male)
        female_count = to_int(raw_female)

        StudentLevelCount.objects.create(
            evaluation_file=evaluation_file,
            level_name=level or f"المستوى {index + 1}",
            male_count=male_count,
            female_count=female_count,
        )


def save_graduate_records(request, evaluation_file):
    years = request.POST.getlist("graduates_year[]")
    male_counts = request.POST.getlist("graduates_male[]")
    female_counts = request.POST.getlist("graduates_female[]")
    total_counts = request.POST.getlist("graduates_total[]")

    for index, year in enumerate(years):
        year = clean_text(year)
        male_count = to_int(male_counts[index] if index < len(male_counts) else 0)
        female_count = to_int(female_counts[index] if index < len(female_counts) else 0)
        total_count = to_int(total_counts[index] if index < len(total_counts) else 0)

        if not year and male_count == 0 and female_count == 0 and total_count == 0:
            continue

        if total_count == 0:
            total_count = male_count + female_count

        GraduateRecord.objects.create(
            evaluation_file=evaluation_file,
            academic_year=year,
            graduates_count=total_count,
            male_count=male_count,
            female_count=female_count,
        )


def save_course_requirement_records(request, evaluation_file):
    column_values = {}

    for field_name, requirement_type in COURSE_REQUIREMENT_COLUMNS:
        column_values[requirement_type] = request.POST.getlist(field_name)

    max_rows = 0

    for values in column_values.values():
        max_rows = max(max_rows, len(values))

    for row_index in range(max_rows):
        for requirement_type, values in column_values.items():
            course_name = clean_text(values[row_index] if row_index < len(values) else "")

            if not course_name:
                continue

            CourseRecord.objects.create(
                evaluation_file=evaluation_file,
                course_name=course_name,
                course_code="",
                credit_hours=0,
                level="",
                requirement_type=requirement_type,
                has_specification=False,
            )


def save_course_specification_records(request, evaluation_file):
    course_names = request.POST.getlist("course_spec_name[]")
    course_codes = request.POST.getlist("course_spec_code[]")
    hours = request.POST.getlist("course_spec_hours[]")
    levels = request.POST.getlist("course_spec_level[]")
    specs = request.POST.getlist("course_spec_available[]")

    for index, course_name in enumerate(course_names):
        course_name = clean_text(course_name)
        course_code = clean_text(course_codes[index] if index < len(course_codes) else "")
        credit_hours = to_int(hours[index] if index < len(hours) else 0)
        level = clean_text(levels[index] if index < len(levels) else "")
        has_specification_value = clean_text(specs[index] if index < len(specs) else "")

        if not course_name and not course_code and credit_hours == 0 and not level:
            continue

        CourseRecord.objects.create(
            evaluation_file=evaluation_file,
            course_name=course_name or "مقرر غير محدد",
            course_code=course_code,
            credit_hours=credit_hours,
            level=level,
            requirement_type=COURSE_SPECIFICATION_TYPE,
            has_specification=(has_specification_value == "نعم"),
        )


def save_course_records(request, evaluation_file):
    save_course_requirement_records(request, evaluation_file)
    save_course_specification_records(request, evaluation_file)


def save_faculty_members(request, evaluation_file):
    names = request.POST.getlist("faculty_name[]")
    qualifications = request.POST.getlist("faculty_qualification[]")
    qualification_years = request.POST.getlist("faculty_qualification_year[]")
    ranks = request.POST.getlist("faculty_rank[]")
    rank_dates = request.POST.getlist("faculty_rank_date[]")
    statuses = request.POST.getlist("faculty_status[]")
    teaching_loads = request.POST.getlist("faculty_teaching_load[]")

    for index, name in enumerate(names):
        name = clean_text(name)
        qualification = clean_text(qualifications[index] if index < len(qualifications) else "")
        academic_rank = clean_text(ranks[index] if index < len(ranks) else "")

        if not name and not qualification and not academic_rank:
            continue

        FacultyMemberRecord.objects.create(
            evaluation_file=evaluation_file,
            name=name or "اسم غير محدد",
            qualification=qualification,
            qualification_year=to_int(
                qualification_years[index] if index < len(qualification_years) else "",
                None,
            ),
            academic_rank=academic_rank,
            rank_date=to_date_or_none(rank_dates[index] if index < len(rank_dates) else ""),
            employment_type=clean_text(statuses[index] if index < len(statuses) else ""),
            teaching_load=clean_text(teaching_loads[index] if index < len(teaching_loads) else "") or None,
        )


def save_infrastructure_records(request, evaluation_file):
    facility_types = request.POST.getlist("facility_type[]")
    counts = request.POST.getlist("facility_count[]")
    areas = request.POST.getlist("facility_area[]")
    equipment_list = request.POST.getlist("facility_equipment[]")
    notes_list = request.POST.getlist("facility_notes[]")

    for index, facility_type in enumerate(facility_types):
        facility_type = clean_text(facility_type)
        count = to_int(counts[index] if index < len(counts) else 0)

        if not facility_type and count == 0:
            continue

        InfrastructureRecord.objects.create(
            evaluation_file=evaluation_file,
            facility_type=facility_type or "مرفق غير محدد",
            count=count,
            area=clean_text(areas[index] if index < len(areas) else ""),
            equipment=clean_text(equipment_list[index] if index < len(equipment_list) else ""),
            notes=clean_text(notes_list[index] if index < len(notes_list) else ""),
        )


def save_library_sources(request, evaluation_file):
    source_types = request.POST.getlist("library_source_type[]")
    titles = request.POST.getlist("library_source_title[]")
    counts = request.POST.getlist("library_source_count[]")
    years = request.POST.getlist("library_source_year[]")
    notes_list = request.POST.getlist("library_source_notes[]")

    for index, title in enumerate(titles):
        source_type = clean_text(source_types[index] if index < len(source_types) else "")
        title = clean_text(title)
        count = to_int(counts[index] if index < len(counts) else 0)

        if not source_type and not title and count == 0:
            continue

        LibrarySourceRecord.objects.create(
            evaluation_file=evaluation_file,
            source_type=source_type or "مصدر غير محدد",
            title=title or "عنوان غير محدد",
            count=count,
            release_year=to_int(years[index] if index < len(years) else "", None),
            notes=clean_text(notes_list[index] if index < len(notes_list) else ""),
        )


def save_education_process_records(request, evaluation_file):
    items = request.POST.getlist("education_item[]")
    statuses = request.POST.getlist("education_status[]")
    values = request.POST.getlist("education_value[]")
    evidences = request.POST.getlist("education_evidence[]")
    notes_list = request.POST.getlist("education_notes[]")

    for index, item in enumerate(items):
        item = clean_text(item)
        status = clean_text(statuses[index] if index < len(statuses) else "")
        value = clean_text(values[index] if index < len(values) else "")

        if not item and not status and not value:
            continue

        EducationProcessRecord.objects.create(
            evaluation_file=evaluation_file,
            item=item or "بند غير محدد",
            status=status,
            value=value,
            evidence=clean_text(evidences[index] if index < len(evidences) else ""),
            notes=clean_text(notes_list[index] if index < len(notes_list) else ""),
        )


def save_tables_data(request, evaluation_file):
    delete_old_table_records(evaluation_file)

    save_student_level_counts(request, evaluation_file)
    save_graduate_records(request, evaluation_file)
    save_course_records(request, evaluation_file)
    save_faculty_members(request, evaluation_file)
    save_infrastructure_records(request, evaluation_file)
    save_library_sources(request, evaluation_file)
    save_education_process_records(request, evaluation_file)

    save_dynamic_tables(request, evaluation_file)
    

def dynamic_table_has_rows(evaluation_file, table_key):
    return DataEntryTableRecord.objects.filter(
        evaluation_file=evaluation_file,
        table_key=table_key
    ).exclude(rows=[]).exists()

def update_standard7_completion(evaluation_file):
    """
    تحديث حالة اكتمال المعيار السابع اعتمادًا على الحقول الجديدة الفعلية
    وليس الحقول القديمة الفارغة الموجودة في cards.
    """

    try:
        standard = QualityStandard.objects.get(number=7)
    except QualityStandard.DoesNotExist:
        return

    entry = StandardEntry.objects.filter(
        evaluation_file=evaluation_file,
        standard=standard
    ).first()

    if not entry:
        return

    form_data = entry.form_data or {}

    required_fields = [
        "library_total_area",
        "library_chairs_count",
        "library_staff_count",
        "library_specialist_staff_count",
        "library_staff_computers_count",
        "library_students_computers_count",
        "library_has_automation",
        "library_university_students_total",
        "library_curriculum_books_count",
        "library_specialized_books_count",
        "library_electronic_sources_count",
    ]

    total_items = len(required_fields)
    filled_items = 0

    for field_name in required_fields:
        if clean_text(form_data.get(field_name)):
            filled_items += 1

    # جدول أبحاث التخرج والرسائل العلمية، إذا كان مطلوبًا ضمن المعيار السابع
    research_has_rows = DataEntryTableRecord.objects.filter(
        evaluation_file=evaluation_file,
        table_key="researchProjectsTable"
    ).exclude(rows=[]).exists()

    total_items += 1

    if research_has_rows:
        filled_items += 1

    if filled_items == 0:
        entry.completion_status = "empty"
        entry.completion_percentage = 0
    elif filled_items >= total_items:
        entry.completion_status = "complete"
        entry.completion_percentage = 100
    else:
        entry.completion_status = "partial"
        entry.completion_percentage = round((filled_items / total_items) * 100)

    entry.save(update_fields=[
        "completion_status",
        "completion_percentage",
        "updated_at",
    ])
def update_standard4_faculty_table_completion(evaluation_file):
    """
    تحديث نسبة المعيار الرابع فقط بسبب جدول أعضاء هيئة التدريس.
    لا نغير منطق المعيار كله، فقط نضيف وجود بيانات جدول أعضاء هيئة التدريس كعنصر محسوب.
    """

    try:
        standard = QualityStandard.objects.get(number=4)
    except QualityStandard.DoesNotExist:
        return

    entry = StandardEntry.objects.filter(
        evaluation_file=evaluation_file,
        standard=standard
    ).first()

    if not entry:
        return

    form_data = entry.form_data or {}

    if not isinstance(form_data, dict):
        form_data = {}

    has_faculty_members = FacultyMemberRecord.objects.filter(
        evaluation_file=evaluation_file
    ).exists()

    # عنصر داخلي فقط للحساب، لا يظهر في الواجهة
    if has_faculty_members:
        form_data["_faculty_members_table_has_rows"] = "yes"
    else:
        form_data.pop("_faculty_members_table_has_rows", None)

    completion_status, completion_percentage = calculate_completion_status(form_data)

    entry.form_data = form_data
    entry.completion_status = completion_status
    entry.completion_percentage = completion_percentage

    entry.save(update_fields=[
        "form_data",
        "completion_status",
        "completion_percentage",
        "updated_at",
    ])    
def update_dynamic_standards_completion(evaluation_file):
    """
    تحديث حالة المعايير التي تعتمد على الجداول الديناميكية.
    لأن بيانات هذه المعايير لا تظهر كلها داخل StandardEntry.form_data.
    """

    dynamic_required_tables = {
        6: [
            "classroomsDataTable",
            "labsDataTable",
        ],
        8: [
            "std8Annex26Table",
            "std8Annex27Table",
            "std8Annex28Table",
            "std8Annex29Table",
            "std8Annex30EducationTable",
            "std8Annex30LibraryTable",
            "std8Annex33Table",
        ],
    }

    for standard_number, table_keys in dynamic_required_tables.items():
        try:
            standard = QualityStandard.objects.get(number=standard_number)
        except QualityStandard.DoesNotExist:
            continue

        entry, created = StandardEntry.objects.get_or_create(
            evaluation_file=evaluation_file,
            standard=standard,
            defaults={
                "form_data": {},
                "saved_as_draft": True,
            }
        )

        total_tables = len(table_keys)
        filled_tables = 0

        for table_key in table_keys:
            if dynamic_table_has_rows(evaluation_file, table_key):
                filled_tables += 1

        if total_tables == 0 or filled_tables == 0:
            entry.completion_status = "empty"
            entry.completion_percentage = 0
        elif filled_tables == total_tables:
            entry.completion_status = "complete"
            entry.completion_percentage = 100
        else:
            entry.completion_status = "partial"
            entry.completion_percentage = round((filled_tables / total_tables) * 100)

        entry.save(update_fields=[
            "completion_status",
            "completion_percentage",
            "updated_at",
        ])
def save_data_entry_to_database(request, standards):
    evaluation_file = get_or_create_evaluation_file(request)

    save_standard_entries(request, evaluation_file, standards)
    save_tables_data(request, evaluation_file)

    update_standard4_faculty_table_completion(evaluation_file)
    update_dynamic_standards_completion(evaluation_file)
    update_standard7_completion(evaluation_file)

    save_mode = clean_text(request.POST.get("save_mode"))

    if save_mode == "draft":
        evaluation_file.status = "draft"
    else:
        all_entries = StandardEntry.objects.filter(evaluation_file=evaluation_file)

        if all_entries.exists() and all_entries.filter(completion_status="complete").count() == all_entries.count():
            evaluation_file.status = "completed"
        else:
            evaluation_file.status = "in_progress"

    evaluation_file.save(update_fields=["status", "updated_at"])

    return evaluation_file


# ============================================================
# Load Saved Data
# ============================================================

def get_selected_evaluation_file(request):
    file_id = clean_text(request.GET.get("file_id"))

    if not file_id:
        return None

    return (
        EvaluationFile.objects
        .select_related("program")
        .filter(id=file_id)
        .first()
    )


def collect_saved_form_data(evaluation_file):
    saved_form_data = {}

    if not evaluation_file:
        return saved_form_data

    entries = (
        StandardEntry.objects
        .filter(evaluation_file=evaluation_file)
        .select_related("standard")
        .order_by("standard__number")
    )

    for entry in entries:
        if isinstance(entry.form_data, dict):
            saved_form_data.update(entry.form_data)

    return saved_form_data


def build_courses_table_rows(evaluation_file):
    requirement_values = {
        "university_requirement": [],
        "college_requirement": [],
        "department_required_requirement": [],
        "program_required_requirement": [],
        "program_optional_requirement": [],
    }

    records = (
        CourseRecord.objects
        .filter(
            evaluation_file=evaluation_file,
            requirement_type__in=list(requirement_values.keys()),
        )
        .order_by("id")
    )

    for record in records:
        if record.requirement_type in requirement_values:
            requirement_values[record.requirement_type].append(clean_text(record.course_name))

    max_rows = 0

    for values in requirement_values.values():
        max_rows = max(max_rows, len(values))

    rows = []

    for index in range(max_rows):
        row = {}

        for requirement_type, field_name in COURSE_REQUIREMENT_TO_FIELD.items():
            values = requirement_values.get(requirement_type, [])
            row[field_name] = values[index] if index < len(values) else ""

        if any(clean_text(value) for value in row.values()):
            rows.append(row)

    return rows


def build_course_specs_table_rows(evaluation_file):
    records = (
        CourseRecord.objects
        .filter(evaluation_file=evaluation_file)
        .filter(
            Q(requirement_type=COURSE_SPECIFICATION_TYPE) |
            Q(requirement_type="") |
            Q(requirement_type__isnull=True)
        )
        .order_by("id")
    )

    rows = []

    for record in records:
        rows.append({
            "course_spec_name[]": clean_text(record.course_name),
            "course_spec_code[]": clean_text(record.course_code),
            "course_spec_hours[]": clean_text(record.credit_hours),
            "course_spec_level[]": clean_text(record.level),
            "course_spec_available[]": "نعم" if record.has_specification else "لا",
        })

    return rows


def build_dynamic_tables_data(evaluation_file):
    saved_tables = {}

    if not evaluation_file:
        return saved_tables

    records = (
        DataEntryTableRecord.objects
        .filter(evaluation_file=evaluation_file)
        .order_by("standard_key", "table_key", "id")
    )

    for record in records:
        if not record.table_key:
            continue

        saved_tables[record.table_key] = record.rows or []

    return saved_tables


def collect_saved_tables_data(evaluation_file):
    saved_tables_data = {
        "admissionCriteriaTable": [],
        "programGoalsTable": [],
        "coursesTable": [],
        "courseSpecsTable": [],
        "facultyTable": [],
        "studentsLevelsTable": [],
        "graduatesTable": [],
        "infrastructureTable": [],
        "librarySourcesTable": [],
        "educationProcessTable": [],
        "outcomesPreparationTable": [],
    }

    if not evaluation_file:
        return saved_tables_data

    standard1_entry = (
        StandardEntry.objects
        .filter(evaluation_file=evaluation_file, standard__number=1)
        .first()
    )

    if standard1_entry and isinstance(standard1_entry.form_data, dict):
        admission_rows = standard1_entry.form_data.get("admissionCriteriaTable", [])

        if isinstance(admission_rows, list):
            saved_tables_data["admissionCriteriaTable"] = admission_rows

    standard2_entry = (
        StandardEntry.objects
        .filter(evaluation_file=evaluation_file, standard__number=2)
        .first()
    )

    if standard2_entry and isinstance(standard2_entry.form_data, dict):
        goals_rows = standard2_entry.form_data.get("programGoalsTable", [])

        if isinstance(goals_rows, list):
            saved_tables_data["programGoalsTable"] = goals_rows

        if not saved_tables_data["programGoalsTable"]:
            old_goals_rows = []

            for index in range(1, 7):
                old_goal = clean_text(standard2_entry.form_data.get(f"goal_{index}", ""))

                if old_goal:
                    old_goals_rows.append({
                        "program_goals[]": old_goal,
                    })

            saved_tables_data["programGoalsTable"] = old_goals_rows

    standard3_entry = (
        StandardEntry.objects
        .filter(evaluation_file=evaluation_file, standard__number=3)
        .first()
    )

    if standard3_entry and isinstance(standard3_entry.form_data, dict):
        outcomes_rows = standard3_entry.form_data.get("outcomesPreparationTable", [])

        if isinstance(outcomes_rows, list):
            saved_tables_data["outcomesPreparationTable"] = outcomes_rows

        if not saved_tables_data["outcomesPreparationTable"]:
            old_value = clean_text(standard3_entry.form_data.get("outcomes_preparation_method", ""))

            if old_value:
                saved_tables_data["outcomesPreparationTable"] = [
                    {
                        "outcomes_preparation[]": old_value,
                    }
                ]

    student_level_rows = []

    student_records = (
        StudentLevelCount.objects
        .filter(evaluation_file=evaluation_file)
        .order_by("id")
    )

    for record in student_records:
        male_count = record.male_count or 0
        female_count = record.female_count or 0

        if male_count == 0 and female_count == 0:
            continue

        student_level_rows.append({
            "student_level[]": clean_text(record.level_name),
            "student_male[]": clean_text(male_count),
            "student_female[]": clean_text(female_count),
            "student_total[]": clean_text(male_count + female_count),
        })

    saved_tables_data["studentsLevelsTable"] = student_level_rows

    saved_tables_data["graduatesTable"] = [
        {
            "graduates_year[]": clean_text(record.academic_year),
            "graduates_male[]": clean_text(getattr(record, "male_count", "")),
            "graduates_female[]": clean_text(getattr(record, "female_count", "")),
            "graduates_total[]": clean_text(record.graduates_count),
        }
        for record in GraduateRecord.objects
        .filter(evaluation_file=evaluation_file)
        .order_by("id")
    ]

    saved_tables_data["coursesTable"] = build_courses_table_rows(evaluation_file)
    saved_tables_data["courseSpecsTable"] = build_course_specs_table_rows(evaluation_file)

    saved_tables_data["facultyTable"] = [
        {
            "faculty_name[]": clean_text(record.name),
            "faculty_qualification[]": clean_text(record.qualification),
            "faculty_qualification_year[]": clean_text(record.qualification_year),
            "faculty_rank[]": clean_text(record.academic_rank),
            "faculty_rank_date[]": date_to_input_value(record.rank_date),
            "faculty_status[]": clean_text(record.employment_type),
            "faculty_teaching_load[]": clean_text(record.teaching_load),
        }
        for record in FacultyMemberRecord.objects
        .filter(evaluation_file=evaluation_file)
        .order_by("id")
    ]

    saved_tables_data["infrastructureTable"] = [
        {
            "facility_type[]": clean_text(record.facility_type),
            "facility_count[]": clean_text(record.count),
            "facility_area[]": clean_text(record.area),
            "facility_equipment[]": clean_text(record.equipment),
            "facility_notes[]": clean_text(record.notes),
        }
        for record in InfrastructureRecord.objects
        .filter(evaluation_file=evaluation_file)
        .order_by("id")
    ]

    saved_tables_data["librarySourcesTable"] = [
        {
            "library_source_type[]": clean_text(record.source_type),
            "library_source_title[]": clean_text(record.title),
            "library_source_count[]": clean_text(record.count),
            "library_source_year[]": clean_text(record.release_year),
            "library_source_notes[]": clean_text(record.notes),
        }
        for record in LibrarySourceRecord.objects
        .filter(evaluation_file=evaluation_file)
        .order_by("id")
    ]

    saved_tables_data["educationProcessTable"] = [
        {
            "education_item[]": clean_text(record.item),
            "education_status[]": clean_text(record.status),
            "education_value[]": clean_text(record.value),
            "education_evidence[]": clean_text(record.evidence),
            "education_notes[]": clean_text(record.notes),
        }
        for record in EducationProcessRecord.objects
        .filter(evaluation_file=evaluation_file)
        .order_by("id")
    ]

    saved_tables_data.update(build_dynamic_tables_data(evaluation_file))

    return saved_tables_data


def build_selected_file_context(selected_evaluation_file):
    selected_program_name = ""
    selected_program_display = ""
    selected_specialty = ""
    selected_academic_year = ""
    selected_start_year = ""

    if not selected_evaluation_file:
        return {
            "selected_program_name": selected_program_name,
            "selected_program_display": selected_program_display,
            "selected_specialty": selected_specialty,
            "selected_academic_year": selected_academic_year,
            "selected_start_year": selected_start_year,
        }

    program = selected_evaluation_file.program

    selected_program_name = clean_text(program.name)
    selected_specialty = clean_text(program.specialization) or "لا يوجد"
    selected_academic_year = clean_text(selected_evaluation_file.academic_year)
    selected_start_year = clean_text(program.start_year)

    if selected_specialty and selected_specialty != "لا يوجد":
        selected_program_display = f"{selected_program_name} - {selected_specialty}"
    else:
        selected_program_display = selected_program_name

    return {
        "selected_program_name": selected_program_name,
        "selected_program_display": selected_program_display,
        "selected_specialty": selected_specialty,
        "selected_academic_year": selected_academic_year,
        "selected_start_year": selected_start_year,
    }

def collect_saved_attachments_data(evaluation_file, standards):
    """
    يرجع كل المرفقات المحفوظة للملف الحالي بصيغة مناسبة للعرض في HTML.
    """

    saved_attachments = {}

    if not evaluation_file:
        return saved_attachments

    # ربط عنوان المرفق باسم الحقل الموجود في HTML
    title_to_field_name = {}

    for standard in standards:
        for attachment in standard.get("attachments", []):
            field_name = attachment.get("name")
            title = attachment.get("label", field_name)

            if field_name and title:
                title_to_field_name[title] = field_name

    entries = (
        StandardEntry.objects
        .filter(evaluation_file=evaluation_file)
        .prefetch_related("attachments")
        .select_related("standard")
        .order_by("standard__number")
    )

    for entry in entries:
        standard_number = entry.standard.number if entry.standard else ""
        standard_title = entry.standard.title if entry.standard else ""

        for attachment in entry.attachments.all():
            field_name = title_to_field_name.get(attachment.title, "")

            if not field_name:
                continue

            file_name = ""
            file_url = ""

            if attachment.file:
                file_name = attachment.file.name.split("/")[-1]
                file_url = attachment.file.url

            saved_attachments.setdefault(field_name, []).append({
                "standard_number": standard_number,
                "standard_title": standard_title,
                "title": attachment.title,
                "file_name": file_name,
                "file_url": file_url,
                "uploaded_at": attachment.uploaded_at.strftime("%Y-%m-%d %H:%M") if attachment.uploaded_at else "",
            })

    return saved_attachments
# ============================================================
# Views
# ============================================================

def home(request):
    programs_count = MainProgram.objects.count()

    standards_count = QualityStandard.objects.filter(is_active=True).count()
    if standards_count == 0:
        standards_count = 8

    draft_standards_count = (
        StandardEvaluationReview.objects
        .filter(review_status="draft")
        .count()
    )

    approved_standards_count = (
        StandardEvaluationReview.objects
        .filter(review_status="reviewed")
        .count()
    )

    evaluations_count = draft_standards_count + approved_standards_count

    improvement_plans_count = (
        StandardEvaluationReview.objects
        .exclude(review_status="empty")
        .exclude(improvement_plan="")
        .count()
    )

    home_alerts = []

    if draft_standards_count > 0:
        home_alerts.append(
            f"يوجد {draft_standards_count} معيار محفوظ كمسودة ولم يتم اعتماده بعد."
        )

    if approved_standards_count == 0 and evaluations_count > 0:
        home_alerts.append(
            "توجد تقييمات محفوظة، لكن لا يوجد أي معيار معتمد حتى الآن."
        )

    if evaluations_count == 0:
        home_alerts.append(
            "لا توجد تقييمات محفوظة حتى الآن. ابدأ من صفحة التقييم بعد إدخال بيانات المعايير."
        )

    # بيانات التشارت في لوحة التحكم
    status_total_count = draft_standards_count + approved_standards_count

    if status_total_count > 0:
        approved_chart_percent = (approved_standards_count / status_total_count) * 100
        draft_chart_percent = (draft_standards_count / status_total_count) * 100
    else:
        approved_chart_percent = 0
        draft_chart_percent = 0

    chart_max_count = max(
        approved_standards_count,
        draft_standards_count,
        improvement_plans_count,
        1,
    )

    approved_bar_width = (approved_standards_count / chart_max_count) * 100
    draft_bar_width = (draft_standards_count / chart_max_count) * 100
    plans_bar_width = (improvement_plans_count / chart_max_count) * 100

    context = {
        "programs_count": programs_count,
        "standards_count": standards_count,
        "evaluations_count": evaluations_count,
        "draft_standards_count": draft_standards_count,
        "approved_standards_count": approved_standards_count,
        "improvement_plans_count": improvement_plans_count,
        "home_alerts": home_alerts,

        "status_total_count": status_total_count,
        "approved_chart_percent": f"{approved_chart_percent:.2f}",
        "draft_chart_percent": f"{draft_chart_percent:.2f}",
        "approved_bar_width": f"{approved_bar_width:.2f}",
        "draft_bar_width": f"{draft_bar_width:.2f}",
        "plans_bar_width": f"{plans_bar_width:.2f}",
    }

    return render(request, "dashboard/home.html", context)

def find_existing_evaluation_file(program_name, specialization, academic_year, exclude_file_id=None):
    program_name = clean_text(program_name)
    specialization = clean_text(specialization)
    academic_year = clean_text(academic_year)

    if specialization in ["لا يوجد", "غير محددة", "-"]:
        specialization = ""

    if not program_name or not academic_year:
        return None

    query = EvaluationFile.objects.select_related("program").filter(
        program__name=program_name,
        program__specialization=specialization,
        academic_year=academic_year,
    )

    # إذا عندك ملفات مؤقتة من القالب لا نعتبرها محفوظة
    query = query.exclude(status="template_preview")

    if exclude_file_id:
        query = query.exclude(id=exclude_file_id)

    return query.first()
# ============================================================
# Programs Dialog Source
# يقرأ البرامج من جدول programs.Program في الأدمن
# ============================================================

def model_has_field(model, field_name):
    return any(field.name == field_name for field in model._meta.fields)


def get_model_text_value(obj, field_names, default=""):
    for field_name in field_names:
        if hasattr(obj, field_name):
            value = getattr(obj, field_name)
            if value is not None:
                return clean_text(value)

    return default


def get_model_year_value(obj, field_names, default=2024):
    for field_name in field_names:
        if hasattr(obj, field_name):
            value = getattr(obj, field_name)
            year = to_int(value, None)
            if year:
                return year

    return default


def build_program_options_for_dialog():
    """
    مصدر البرامج في Dialog إدخال البيانات.

    يقرأ أولًا من:
        programs.Program

    وهو الجدول الظاهر عندك في:
        /admin/programs/program/add/

    وإذا لم يجده لأي سبب، يرجع احتياطيًا إلى AcademicProgram.
    """

    try:
        ProgramModel = apps.get_model("programs", "Program")
    except LookupError:
        ProgramModel = None

    program_map = {}

    # --------------------------------------------------------
    # المصدر الأساسي: جدول البرامج في تطبيق programs
    # --------------------------------------------------------
    if ProgramModel is not None:
        programs_qs = ProgramModel.objects.all()

        if model_has_field(ProgramModel, "is_active"):
            programs_qs = programs_qs.filter(is_active=True)

        elif model_has_field(ProgramModel, "active"):
            programs_qs = programs_qs.filter(active=True)

        if model_has_field(ProgramModel, "name"):
            programs_qs = programs_qs.order_by("name", "id")

        elif model_has_field(ProgramModel, "program_name"):
            programs_qs = programs_qs.order_by("program_name", "id")

        else:
            programs_qs = programs_qs.order_by("id")

        for program in programs_qs:
            program_name = get_model_text_value(
                program,
                [
                    "name",
                    "program_name",
                    "title",
                    "program_title",
                ],
            )

            if not program_name:
                continue

            specialization = get_model_text_value(
                program,
                [
                    "specialization",
                    "specialty",
                    "track",
                    "path",
                    "major",
                ],
            )

            if specialization in ["لا يوجد", "غير محددة", "-"]:
                specialization = ""

            start_year = get_model_year_value(
                program,
                [
                    "start_year",
                    "establishment_year",
                    "program_establishment_year",
                    "created_year",
                    "year",
                ],
                default=2024,
            )

            if program_name not in program_map:
                program_map[program_name] = {
                    "name": program_name,
                    "start_year": start_year,
                    "specialties": [],
                }

            if specialization:
                exists = any(
                    item["name"] == specialization
                    for item in program_map[program_name]["specialties"]
                )

                if not exists:
                    program_map[program_name]["specialties"].append({
                        "name": specialization,
                        "start_year": start_year,
                    })

            else:
                if start_year and not program_map[program_name].get("start_year"):
                    program_map[program_name]["start_year"] = start_year

    # --------------------------------------------------------
    # مصدر احتياطي: AcademicProgram
    # --------------------------------------------------------
    else:
        programs_qs = (
            AcademicProgram.objects
            .filter(is_active=True)
            .order_by("name", "specialization", "start_year", "id")
        )

        for program in programs_qs:
            program_name = clean_text(program.name)
            specialization = clean_text(program.specialization)

            if not program_name:
                continue

            if specialization in ["لا يوجد", "غير محددة", "-"]:
                specialization = ""

            start_year = program.start_year or 2024

            if program_name not in program_map:
                program_map[program_name] = {
                    "name": program_name,
                    "start_year": start_year,
                    "specialties": [],
                }

            if specialization:
                program_map[program_name]["specialties"].append({
                    "name": specialization,
                    "start_year": start_year,
                })

    program_options = list(program_map.values())

    for item in program_options:
        item["specialties"] = sorted(
            item["specialties"],
            key=lambda specialty: specialty["name"]
        )

    return sorted(program_options, key=lambda item: item["name"])
def get_posted_standard_label(post_data, standards):
    active_standard_id = clean_text(post_data.get("active_standard_id"))
    active_standard_title = clean_text(post_data.get("active_standard_title"))

    if active_standard_title:
        return active_standard_title

    if not active_standard_id:
        return "ملف التقييم كامل"

    for index, standard in enumerate(standards, start=1):
        standard_id = str(getattr(standard, "id", "") or standard.get("id", ""))
        standard_title = (
            getattr(standard, "title", "")
            or getattr(standard, "name", "")
            or standard.get("title", "")
            or standard.get("name", "")
        )

        if standard_id == active_standard_id:
            return f"المعيار {index}: {standard_title}"

    return "ملف التقييم كامل"
def get_edited_standard_labels_from_post(post_data):
    raw_labels = post_data.get("edited_standards_json", "[]")
    active_label = clean_text(post_data.get("active_standard_title"))

    labels = []

    try:
        parsed_labels = json.loads(raw_labels)
    except json.JSONDecodeError:
        parsed_labels = []

    if isinstance(parsed_labels, list):
        for label in parsed_labels:
            label = clean_text(label)

            if label and label not in labels:
                labels.append(label)

    # في حال لم يتم التقاط أي تعديل، نسجل التبويب النشط كحل احتياطي.
    if not labels:
        labels.append(active_label or "ملف التقييم كامل")

    return labels
def data_entry(request):
    standards = get_data_entry_standards_from_admin()

    if request.method == "POST":
        post_data = request.POST.copy()
        edited_standard_labels = get_edited_standard_labels_from_post(post_data)
        evaluation_file_id = clean_text(post_data.get("evaluation_file_id"))

        current_file = None
        if evaluation_file_id:
            current_file = (
                EvaluationFile.objects
                .select_related("program")
                .filter(id=evaluation_file_id)
                .first()
            )

        selected_program = clean_text(post_data.get("selected_program"))
        selected_specialty = clean_text(post_data.get("selected_specialty"))
        selected_academic_year = clean_text(post_data.get("selected_academic_year"))
        selected_start_year = clean_text(post_data.get("selected_start_year"))

        is_update_operation = current_file is not None

        # عند تعديل ملف محفوظ، نعتمد بيانات البرنامج والسنة من الملف نفسه
        # إذا كانت الحقول المرسلة من الواجهة فارغة.
        if current_file:
            if not selected_program:
                selected_program = clean_text(current_file.program.name)

            if not selected_specialty:
                selected_specialty = clean_text(current_file.program.specialization)

            if selected_specialty in ["لا يوجد", "غير محددة", "-"]:
                selected_specialty = ""

            if not selected_academic_year:
                selected_academic_year = clean_text(current_file.academic_year)

            if not selected_start_year:
                selected_start_year = clean_text(current_file.program.start_year)

            post_data["selected_program"] = selected_program
            post_data["selected_specialty"] = selected_specialty
            post_data["selected_academic_year"] = selected_academic_year
            post_data["selected_start_year"] = selected_start_year
            request.POST = post_data

        existing_file = find_existing_evaluation_file(
            selected_program,
            selected_specialty,
            selected_academic_year,
            exclude_file_id=evaluation_file_id,
        )

        if existing_file:
            messages.error(
                request,
                (
                    f"هذا الملف موجود مسبقًا: {existing_file.program} - "
                    f"سنة التقييم: {selected_academic_year}. "
                    "اختاري سنة أخرى أو افتحي الملف من الملفات المحفوظة."
                ),
            )

            if evaluation_file_id:
                return redirect(
                    f"{reverse('data_entry')}?file_id={evaluation_file_id}"
                )

            return redirect("data_entry")

        evaluation_file = save_data_entry_to_database(request, standards)

        action_type = "update" if is_update_operation else "create"
        action_text = "تعديل" if is_update_operation else "إضافة"

        for standard_label in edited_standard_labels:
            log_activity(
                request=request,
                action=action_type,
                section="إدخال بيانات المعايير",
                standard_label=standard_label,
                model_name="ملف تقييم",
                object_id=evaluation_file.id,
                object_repr=(
                    f"{evaluation_file.program} - "
                    f"{evaluation_file.academic_year}"
                ),
                changes=(
                    f"تمت عملية {action_text} بيانات هذا المعيار "
                    "من النظام الرئيسي."
                ),
            )

        messages.success(
            request,
            f"تم حفظ بيانات ملف التقييم: {evaluation_file}",
        )

        return redirect(
            f"{reverse('data_entry')}?file_id={evaluation_file.id}"
        )

    evaluation_files = (
        EvaluationFile.objects
        .select_related("program")
        .exclude(status="template_preview")
        .annotate(saved_standards_count=Count("standard_entries"))
        .order_by("-updated_at")
    )

    selected_evaluation_file = get_selected_evaluation_file(request)

    if request.GET.get("file_id") and not selected_evaluation_file:
        messages.warning(request, "لم يتم العثور على ملف التقييم المطلوب.")

    selected_context = build_selected_file_context(selected_evaluation_file)
    saved_form_data = collect_saved_form_data(selected_evaluation_file)
    saved_tables_data = collect_saved_tables_data(selected_evaluation_file)
    saved_attachments_data = collect_saved_attachments_data(
        selected_evaluation_file,
        standards,
    )

    graduation_year_options = build_graduation_year_options(
        selected_context.get("selected_start_year"),
        selected_context.get("selected_academic_year"),
    )

    program_options = build_program_options_for_dialog()

    context = {
        "standards": standards,
        "page_title": "إدخال بيانات البرنامج الأكاديمي",
        "program_options": program_options,
        "programs": [program["name"] for program in program_options],
        
        "evaluation_files": evaluation_files,
        "selected_evaluation_file": selected_evaluation_file,
        "graduation_year_options": graduation_year_options,
        "selected_program_name": selected_context["selected_program_name"],
        "selected_program_display": selected_context["selected_program_display"],
        "selected_specialty": selected_context["selected_specialty"],
        "selected_academic_year": selected_context["selected_academic_year"],
        "selected_start_year": selected_context["selected_start_year"],
        "saved_form_data_json": saved_form_data,
        "saved_tables_data_json": saved_tables_data,
        "saved_attachments_data_json": saved_attachments_data,
    }

    return render(request, "dashboard/data_entry.html", context)


def evaluation(request):
    return render(request, "dashboard/evaluation.html")





def improvement_plans(request):
    return render(request, "dashboard/improvement_plans.html")


def reports(request):
    return render(request, "dashboard/reports.html")


def system_management(request):
    return render(request, "dashboard/system_management.html")
def _get_safe_next_url(request):
    """
    تحديد الوجهة الآمنة بعد تسجيل الدخول.

    يمنع إعادة المستخدم إلى:
    - بوابة الدخول /
    - صفحة تسجيل الدخول نفسها
    """

    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or ""
    ).strip()

    home_url = reverse("home")
    gateway_url = reverse("login_gateway")
    system_login_url = reverse("system_login")

    blocked_destinations = {
        "",
        "/",
        gateway_url,
        system_login_url,
    }

    if next_url in blocked_destinations:
        return home_url

    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url

    return home_url


@login_not_required
@never_cache
@ensure_csrf_cookie
@csrf_protect
@require_http_methods(["GET", "POST"])
def system_login_view(request):
    raw_next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or ""
    ).strip()

    admin_index_url = reverse("admin:index")

    is_admin_login = (
        request.path.startswith("/admin/")
        or raw_next_url.startswith("/admin/")
    )

    # المستخدم مسجل مسبقًا
    if request.user.is_authenticated:
        safe_next = _get_safe_next_url(request)

        if is_admin_login:
            if request.user.is_staff:
                return redirect(admin_index_url)

            messages.error(
                request,
                "حسابك لا يملك صلاحية الدخول إلى لوحة الإدارة.",
            )

            logout(request)

            return redirect(
                reverse("system_login")
            )

        return redirect(safe_next)

    if request.method == "POST":
        form = AuthenticationForm(
            request=request,
            data=request.POST,
        )

        if form.is_valid():
            user = form.get_user()

            login(request, user)

            safe_next = _get_safe_next_url(request)

            if safe_next.startswith("/admin/"):
                if user.is_staff:
                    return redirect(safe_next)

                messages.error(
                    request,
                    "حسابك لا يملك صلاحية الدخول إلى لوحة الإدارة.",
                )

                logout(request)

                return redirect(
                    reverse("system_login")
                )

            return redirect(safe_next)

        messages.error(
            request,
            "اسم المستخدم أو كلمة المرور غير صحيحة.",
        )

    else:
        form = AuthenticationForm(
            request=request,
        )

    next_value = raw_next_url

    if next_value in {
        "",
        "/",
        reverse("login_gateway"),
        reverse("system_login"),
    }:
        next_value = ""

    return render(
        request,
        "dashboard/system_login.html",
        {
            "form": form,
            "next": next_value,
        },
    )


@require_POST
def system_logout_view(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)
