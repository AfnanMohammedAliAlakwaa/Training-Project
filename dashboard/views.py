import json

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Q
from django.urls import reverse

from .models import (
    AcademicProgram,
    EvaluationFile,
    QualityStandard,
    StandardEntry,
    EvidenceAttachment,
    StudentLevelCount,
    GraduateRecord,
    CourseRecord,
    FacultyMemberRecord,
    InfrastructureRecord,
    LibrarySourceRecord,
    EducationProcessRecord,
    DataEntryTableRecord,
)


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
            "weight": "10%",
            "cards": [
                {
                    "title": "القاعات الدراسية والمعامل",
                    "fields": [
                        {
                            "label": "عدد القاعات الدراسية",
                            "name": "classrooms_count",
                            "type": "number",
                        },
                        {
                            "label": "المساحة الإجمالية للقاعات م²",
                            "name": "classrooms_total_area",
                            "type": "number",
                        },
                        {
                            "label": "عدد المختبرات / المعامل",
                            "name": "labs_total_count",
                            "type": "number",
                        },
                        {
                            "label": "المساحة الإجمالية للمعامل م²",
                            "name": "labs_total_area",
                            "type": "number",
                        },
                        {
                            "label": "عدد الورش / المشاغل",
                            "name": "workshops_count",
                            "type": "number",
                        },
                        {
                            "label": "عدد الفنيين",
                            "name": "infrastructure_technicians_count",
                            "type": "number",
                        },
                        {
                            "label": "نسبة أجهزة الحاسب إلى الطلبة",
                            "name": "computer_student_ratio",
                            "type": "text",
                            "placeholder": "مثال: 1:4",
                        },
                        {
                            "label": "ملاحظات حول كفاية القاعات والمعامل والتجهيزات",
                            "name": "infrastructure_notes",
                            "type": "textarea",
                            "full": True,
                        },
                    ],
                },
            ],
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


# ============================================================
# Program and Evaluation File
# ============================================================

def get_or_create_program_from_request(request):
    program_name = clean_text(request.POST.get("selected_program"))
    specialization = clean_text(request.POST.get("selected_specialty"))
    start_year = to_int(request.POST.get("selected_start_year"), None)

    if specialization in ["لا يوجد", "غير محددة", "-"]:
        specialization = ""

    if not program_name:
        program_name = "برنامج غير محدد"

    program, created = AcademicProgram.objects.get_or_create(
        name=program_name,
        specialization=specialization,
        defaults={
            "start_year": start_year,
            "is_active": True,
        },
    )

    updated = False

    if start_year and program.start_year != start_year:
        program.start_year = start_year
        updated = True

    if not program.is_active:
        program.is_active = True
        updated = True

    if updated:
        program.save()

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
        quality_standard, created = QualityStandard.objects.update_or_create(
            number=index,
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


def normalize_dynamic_cell_value(value):
    if isinstance(value, list):
        return [clean_text(item) for item in value if clean_text(item)]

    return clean_text(value)


def dynamic_row_has_value(row):
    for key, value in row.items():
        if str(key).startswith("__"):
            continue

        if isinstance(value, list):
            if any(clean_text(item) for item in value):
                return True
        else:
            if clean_text(value):
                return True

    return False


def save_dynamic_tables(request, evaluation_file):
    raw_json = request.POST.get("dynamic_tables_json", "")

    if not raw_json:
        return

    try:
        tables_payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return

    if not isinstance(tables_payload, dict):
        return

    DataEntryTableRecord.objects.filter(
        evaluation_file=evaluation_file
    ).delete()

    for table_key, table_data in tables_payload.items():
        table_key = clean_text(table_key)

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


def save_data_entry_to_database(request, standards):
    evaluation_file = get_or_create_evaluation_file(request)

    save_standard_entries(request, evaluation_file, standards)
    save_tables_data(request, evaluation_file)

    save_mode = clean_text(request.POST.get("save_mode"))

    if save_mode == "draft":
        evaluation_file.status = "draft"
    elif evaluation_file.status == "draft":
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
    return render(request, "dashboard/home.html")


def data_entry(request):
    standards = get_data_entry_standards()

    if request.method == "POST":
        
        
        evaluation_file = save_data_entry_to_database(request, standards)

        messages.success(
            request,
            f"تم حفظ بيانات ملف التقييم: {evaluation_file}"
        )

        return redirect(f"{reverse('data_entry')}?file_id={evaluation_file.id}")

    evaluation_files = (
        EvaluationFile.objects
        .select_related("program")
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
    standards
)

    graduation_year_options = build_graduation_year_options(
        selected_context.get("selected_start_year"),
        selected_context.get("selected_academic_year"),
    )

    context = {
        "standards": standards,
        "page_title": "إدخال بيانات البرنامج الأكاديمي",
        "programs": [
            "تقنية المعلومات",
            "نظم المعلومات",
            "علوم الحاسوب",
            "الأمن السيبراني",
        ],
        "academic_years": [
            "2024-2025",
            "2025-2026",
            "2026-2027",
        ],
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

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import EvaluationFile


@require_POST
def delete_evaluation_file(request, file_id):
    evaluation_file = get_object_or_404(EvaluationFile, id=file_id)

    evaluation_file.delete()

    messages.success(request, "تم حذف ملف التقييم والبيانات المرتبطة به بنجاح.")
    return redirect("data_entry")


def evaluation(request):
    return render(request, "dashboard/evaluation.html")


def analysis(request):
    return render(request, "dashboard/analysis.html")


def improvement_plans(request):
    return render(request, "dashboard/improvement_plans.html")


def reports(request):
    return render(request, "dashboard/reports.html")


def system_management(request):
    return render(request, "dashboard/system_management.html")