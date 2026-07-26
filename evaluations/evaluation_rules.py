# evaluation_rules.py
# قواعد التقييم الآلي المتوافقة مع أسماء الحقول والجداول الفعلية
# في صفحة إدخال البيانات.

STANDARD_EVALUATION_RULES = [
    {
        "number": 1,
        "title": "المعيار الأول: معلومات البرنامج",
        "weight": 5,
        "indicators": [
            {
                "key": "std1_general_program_info",
                "text": "اكتمال المعلومات العامة الأساسية للبرنامج.",
                "fields": [
                    "program_name",
                    "qualification_type",
                    "program_type",
                    "study_system",
                    "program_duration",
                    "initial_license_date",
                    "initial_license_type",
                    "program_phone",
                    "program_website",
                    "program_email",
                    "program_address",
                ],
            },
            {
                "key": "std1_manager_info",
                "text": "اكتمال المعلومات الأساسية لمسؤول البرنامج.",
                "fields": [
                    "manager_name",
                    "manager_job_type",
                    "manager_qualification",
                    "manager_rank",
                    "manager_nationality",
                    "manager_appointment_date",
                    "appointment_authority",
                    "appointment_number",
                    "appointment_date",
                    "manager_personal_phone",
                    "manager_email",
                ],
            },
            {
                "key": "std1_program_overview",
                "text": "توفر نبذة وبيانات تعريفية عن البرنامج.",
                "fields": [
                    "program_overview",
                    "program_establishment_year",
                    "college_name",
                    "department_name",
                ],
            },
            {
                "key": "std1_admission",
                "text": "توفر معايير القبول والطاقة الاستيعابية.",
                "form_tables": ["admissionCriteriaTable"],
                "fields": ["admission_capacity"],
            },
            {
                "key": "std1_faculty_summary",
                "text": "توفر ملخص أعداد هيئة التدريس والفنيين.",
                "fields": [
                    "phd_faculty_count",
                    "fulltime_faculty_total",
                    "supporting_faculty_total",
                    "technicians_count",
                ],
            },
            {
                "key": "std1_students_graduates",
                "text": "توفر الأعداد الإجمالية للطلبة والخريجين.",
                "fields": [
                    "current_students_count",
                    "graduates_count",
                ],
            },
        ],
    },
    {
        "number": 2,
        "title": "المعيار الثاني: رسالة وأهداف وخطط البرنامج",
        "weight": 10,
        "indicators": [
            {
                "key": "std2_mission",
                "text": "توفر نص رسالة البرنامج.",
                "fields": ["program_mission"],
            },
            {
                "key": "std2_goals",
                "text": "توفر أهداف البرنامج.",
                "form_tables": ["programGoalsTable"],
            },
        ],
    },
    {
        "number": 3,
        "title": "المعيار الثالث: مخرجات تعلم البرنامج",
        "weight": 15,
        "indicators": [
            {
                "key": "std3_learning_outcomes",
                "text": "اكتمال مخرجات التعلم في المجالات الأربعة.",
                "fields": [
                    "knowledge_skills",
                    "mental_skills",
                    "practical_skills",
                    "life_skills",
                ],
            },
            {
                "key": "std3_preparation",
                "text": "توفر بيانات إعداد مخرجات التعلم.",
                "form_tables": ["outcomesPreparationTable"],
            },
        ],
    },
    {
        "number": 4,
        "title": "المعيار الرابع: مواصفات البرنامج الأكاديمي",
        "weight": 15,
        "indicators": [
            {
                "key": "std4_psd",
                "text": "توفر وثيقة توصيف البرنامج.",
                "field_values": {"has_psd": ["نعم"]},
            },
            {
                "key": "std4_credit_hours",
                "text": "اكتمال بيانات الخطة والساعات المعتمدة.",
                "fields": [
                    "total_credit_hours",
                    "university_requirements_hours",
                    "college_requirements_hours",
                    "department_requirements_hours",
                    "major_required_hours",
                    "major_optional_hours",
                ],
            },
            {
                "key": "std4_courses",
                "text": "توفر بيانات مقررات الخطة الدراسية.",
                "record_checks": ["courses"],
            },
            {
                "key": "std4_course_specs",
                "text": "توفر بيانات توصيف المقررات.",
                "record_checks": ["course_specs"],
            },
            {
                "key": "std4_faculty",
                "text": "توفر بيانات أعضاء هيئة التدريس.",
                "record_checks": ["faculty"],
            },
            {
                "key": "std4_teaching_hours",
                "text": "اكتمال بيانات الساعات التدريسية.",
                "fields": [
                    "fulltime_teaching_hours",
                    "parttime_teaching_hours",
                    "program_total_teaching_hours",
                    "fulltime_parttime_teaching_percentage",
                    "phd_teaching_hours",
                    "phd_teaching_hours_percentage",
                ],
            },
        ],
    },
    {
        "number": 5,
        "title": "المعيار الخامس: الطلبة",
        "weight": 10,
        "indicators": [
            {
                "key": "std5_levels",
                "text": "توفر أعداد الطلبة حسب المستويات.",
                "record_checks": ["student_levels"],
            },
            {
                "key": "std5_graduates",
                "text": "توفر بيانات الخريجين حسب السنوات.",
                "record_checks": ["graduates"],
            },
            {
                "key": "std5_success",
                "text": "اكتمال بيانات معدلات النجاح.",
                "fields": [
                    "male_success_rate",
                    "female_success_rate",
                    "average_success_rate",
                ],
            },
            {
                "key": "std5_gpa",
                "text": "اكتمال بيانات المعدل التراكمي.",
                "fields": [
                    "male_cumulative_gpa",
                    "female_cumulative_gpa",
                    "average_cumulative_gpa",
                ],
            },
            {
                "key": "std5_progress",
                "text": "اكتمال مؤشرات التقدم والبقاء والتدفق والانسحاب.",
                "fields": [
                    "average_progress_rate",
                    "average_retention_rate",
                    "average_flow_rate",
                    "average_withdrawal_rate",
                ],
            },
        ],
    },
    {
        "number": 6,
        "title": "المعيار السادس: البنية التحتية للبرنامج",
        "weight": 10,
        "indicators": [
            {
                "key": "std6_classrooms",
                "text": "توفر بيانات القاعات الدراسية وتجهيزاتها.",
                "dynamic_tables": ["classroomsDataTable"],
            },
            {
                "key": "std6_labs",
                "text": "توفر بيانات المعامل والمختبرات وتجهيزاتها.",
                "dynamic_tables": ["labsDataTable"],
            },
            {
                "key": "std6_infrastructure",
                "text": "توفر سجلات مرافق البنية التحتية ونتائج المطابقة.",
                "record_checks": ["infrastructure"],
            },
        ],
    },
    {
        "number": 7,
        "title": "المعيار السابع: المكتبة",
        "weight": 10,
        "indicators": [
            {
                "key": "std7_equipment",
                "text": "اكتمال بيانات مساحة المكتبة وتجهيزاتها ومواردها البشرية.",
                "fields": [
                    "library_total_area",
                    "library_chairs_count",
                    "library_staff_count",
                    "library_specialist_staff_count",
                    "library_staff_computers_count",
                    "library_students_computers_count",
                    "library_has_automation",
                    "library_university_students_total",
                ],
            },
            {
                "key": "std7_books",
                "text": "اكتمال الأعداد الإجمالية لمصادر المكتبة.",
                "fields": [
                    "library_curriculum_books_count",
                    "library_specialized_books_count",
                    "library_electronic_sources_count",
                ],
            },
            {
                "key": "std7_sources",
                "text": "توفر قائمة تفصيلية بمصادر المكتبة.",
                "record_checks": ["library_sources"],
            },
            {
                "key": "std7_research",
                "text": "توفر بيانات أبحاث التخرج والرسائل العلمية.",
                "dynamic_tables": ["researchProjectsTable"],
            },
        ],
    },
    {
        "number": 8,
        "title": "المعيار الثامن: إدارة العملية التعليمية",
        "weight": 25,
        "indicators": [
            {
                "key": "std8_annex26",
                "text": "توفر بيانات الساعات والجداول والمحاضرات المنفذة.",
                "dynamic_tables": ["std8Annex26Table"],
            },
            {
                "key": "std8_annex27",
                "text": "توفر بيانات متابعة الأنشطة والتكاليف والتدريب.",
                "dynamic_tables": ["std8Annex27Table"],
            },
            {
                "key": "std8_annex28",
                "text": "توفر بيانات متابعة موضوعات أبحاث التخرج وتنفيذها.",
                "dynamic_tables": ["std8Annex28Table"],
            },
            {
                "key": "std8_annex29",
                "text": "توفر نتائج رضا أعضاء هيئة التدريس.",
                "dynamic_tables": ["std8Annex29Table"],
            },
            {
                "key": "std8_annex30_education",
                "text": "توفر نتائج رضا الطلبة عن الخدمات التعليمية.",
                "dynamic_tables": ["std8Annex30EducationTable"],
            },
            {
                "key": "std8_annex30_library",
                "text": "توفر نتائج رضا الطلبة عن الخدمات المكتبية.",
                "dynamic_tables": ["std8Annex30LibraryTable"],
            },
            {
                "key": "std8_annex33",
                "text": "توفر نتائج تقييم سير العملية الامتحانية.",
                "dynamic_tables": ["std8Annex33Table"],
            },
        ],
    },
]
