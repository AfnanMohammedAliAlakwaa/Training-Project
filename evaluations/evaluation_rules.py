STANDARD_EVALUATION_RULES = [
    {
        "number": 1,
        "title": "المعيار الأول: معلومات البرنامج",
        "weight": 5,
        "indicators": [
            {
                "key": "std1_general_program_info",
                "text": "المعلومات العامة عن البرنامج مكتملة.",
                "fields": [
                    "program_name",
                    "qualification_type",
                    "program_type",
                    "study_system",
                    "program_duration",
                    "initial_license_date",
                    "initial_license_type",
                    "program_phone",
                    "program_fax",
                    "program_website",
                    "program_email",
                    "postal_box",
                    "program_address",
                ],
            },
            {
                "key": "std1_manager_info",
                "text": "المعلومات العامة عن مسؤول البرنامج مكتملة.",
                "fields": [
                    "manager_name",
                    "manager_job_type",
                    "manager_qualification",
                    "manager_rank",
                    "manager_appointment_date",
                    "appointment_authority",
                    "appointment_number",
                    "appointment_date",
                    "manager_email",
                ],
                "attachments": [
                    "ملحق 1: السيرة الذاتية لمسؤول البرنامج",
                    "ملحق 2: قرار تعيين مسؤول البرنامج",
                ],
            },
            {
                "key": "std1_admission_criteria",
                "text": "يتوفر لدى البرنامج معايير قبول الطلبة.",
                "form_tables": ["admissionCriteriaTable"],
                "fields": ["admission_capacity"],
                "attachments": [
                    "ملحق 3: معايير القبول والطاقة الاستيعابية",
                ],
            },
            {
                "key": "std1_capacity",
                "text": "يلتزم البرنامج بالطاقة الاستيعابية المحددة.",
                "fields": ["admission_capacity"],
            },
            {
    "key": "std1_faculty_list",
    "text": "تتوفر بيانات أعضاء هيئة التدريس والفنيين في البرنامج.",
    "fields": [
        "phd_faculty_count",
        "fulltime_faculty_total",
        "supporting_faculty_total",
        "technicians_count",
    ],
},
{
    "key": "std1_graduates_count",
    "text": "تتوفر بيانات أعداد الخريجين.",
    "fields": [
        "graduates_count",
    ],
},
{
    "key": "std1_students_count",
    "text": "تتوفر بيانات أعداد الطلبة المقيدين حاليًا.",
    "fields": [
        "current_students_count",
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
                "text": "تتوفر رسالة واضحة ومعتمدة للبرنامج.",
                "fields": ["program_mission"],
                "attachments": [
                    "ملحق 8: أدلة ورشة إعداد رسالة البرنامج ومحاضر الاعتماد",
                ],
            },
            {
                "key": "std2_goals",
                "text": "تتوفر أهداف البرنامج وتم إعدادها واعتمادها بصورة مناسبة.",
                "form_tables": ["programGoalsTable"],
                "attachments": [
                    "ملحق 9: أدلة إعداد أهداف البرنامج ومحاضر الاعتماد",
                ],
            },
            {
                "key": "std2_alignment",
                "text": "تتسق رسالة وأهداف البرنامج مع رسالة الكلية والجامعة.",
                "attachments": [
                    "ملحق 10: اتساق الرسالة والأهداف مع رسالة الكلية والجامعة",
                ],
            },
            {
                "key": "std2_executive_plan",
                "text": "تتوفر خطة تنفيذية للبرنامج.",
                "attachments": [
                    "ملحق 11: الخطة التنفيذية للبرنامج",
                ],
            },
        ],
    },
    {
        "number": 3,
        "title": "المعيار الثالث: مخرجات تعلم البرنامج",
        "weight": 15,
        "indicators": [
            {
                "key": "std3_outcomes_available",
                "text": "يتوفر لدى البرنامج مخرجات تعلم.",
                "fields": [
                    "knowledge_skills",
                    "mental_skills",
                    "practical_skills",
                    "life_skills",
                ],
            },
            {
                "key": "std3_outcomes_workshop",
                "text": "تم إعداد مخرجات التعلم من خلال ورشة خاصة.",
                "form_tables": ["outcomesPreparationTable"],
                "attachments": [
                    "ملحق 13: أدبيات ورشة إعداد وثيقة توصيف البرنامج",
                ],
            },
            {
                "key": "std3_outcomes_measurement",
                "text": "هناك قياس لمخرجات التعلم من قبل الطلبة والخريجين وأعضاء هيئة التدريس.",
                "attachments": [
                    "ملحق 14: أدلة قياس مخرجات التعلم ورضا سوق العمل",
                ],
            },
            {
                "key": "std3_labor_market",
                "text": "هناك قياس لمخرجات التعلم من قبل سوق العمل.",
                "attachments": [
                    "ملحق 14: أدلة قياس مخرجات التعلم ورضا سوق العمل",
                ],
            },
            {
                "key": "std3_improvement_plan",
                "text": "يوجد لدى البرنامج خطة لتحسين مخرجات التعلم.",
                "attachments": [
                    "ملحق 14: أدلة قياس مخرجات التعلم ورضا سوق العمل",
                ],
            },
        ],
    },
    {
    "number": 4,
    "title": "المعيار الرابع: مواصفات البرنامج الأكاديمي",
    "weight": 15,
    "indicators": [
        {
            "key": "std4_program_spec",
            "text": "يمتلك البرنامج وثيقة توصيف معتمدة.",
            "field_values": {
                "has_psd": ["نعم"],
            },
        },
        {
            "key": "std4_study_plan",
            "text": "تتوفر خطة دراسية مكتملة تبين توزيع الساعات المعتمدة.",
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
            "key": "std4_courses_plan",
            "text": "الخطة الدراسية تبين المقررات وتصنيفها وتسلسلها وساعاتها.",
            "record_checks": [
                "courses",
            ],
        },
        {
            "key": "std4_course_specs",
            "text": "يتوفر ملف متكامل ومحدث لكل مقرر دراسي.",
            "record_checks": [
                "course_specs",
            ],
        },
        {
            "key": "std4_faculty_members",
            "text": "تتوفر بيانات أعضاء هيئة التدريس ومساعديهم.",
            "record_checks": [
                "faculty",
            ],
        },
        {
            "key": "std4_teaching_hours",
            "text": "تتوفر بيانات الساعات التدريسية للمتفرغين وغير المتفرغين وحملة الدكتوراه.",
            "fields": [
                "fulltime_teaching_hours",
                "parttime_teaching_hours",
                "phd_teaching_hours",
                "program_total_teaching_hours",
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
                "key": "std5_student_levels",
                "text": "تتوفر أعداد الطلبة حسب المستويات.",
                "record_checks": ["student_levels"],
            },
            {
                "key": "std5_graduates",
                "text": "تتوفر بيانات الخريجين حسب السنوات.",
                "record_checks": ["graduates"],
            },
            {
                "key": "std5_success_rate",
                "text": "تتوفر معدلات النجاح للطلبة.",
                "fields": [
                    "male_success_rate",
                    "female_success_rate",
                    "average_success_rate",
                ],
            },
            {
                "key": "std5_gpa",
                "text": "تتوفر بيانات المعدل التراكمي للخريجين.",
                "fields": [
                    "male_cumulative_gpa",
                    "female_cumulative_gpa",
                    "average_cumulative_gpa",
                ],
            },
            {
                "key": "std5_progress_retention",
                "text": "تتوفر مؤشرات التقدم والبقاء والتدفق والانسحاب.",
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
                "text": "تتوفر بيانات القاعات الدراسية ومساحاتها وتجهيزاتها.",
                "dynamic_tables": ["classroomsDataTable"],
            },
            {
                "key": "std6_labs",
                "text": "تتوفر بيانات المختبرات والمعامل ومساحاتها وتجهيزاتها.",
                "dynamic_tables": ["labsDataTable"],
            },
            {
                "key": "std6_infrastructure_records",
                "text": "تتوفر بيانات مرافق البنية التحتية للبرنامج.",
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
                "key": "std7_library_equipment",
                "text": "تتوفر بيانات تجهيزات المكتبة ومساحتها ومقاعدها وحوسبتها.",
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
                "key": "std7_library_sources",
                "text": "تتوفر مصادر المكتبة والمراجع المرتبطة بالبرنامج.",
                "record_checks": ["library_sources"],
            },
            {
                "key": "std7_research_projects",
                "text": "تتوفر بيانات أبحاث التخرج والرسائل العلمية.",
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
                "text": "تتوفر بيانات عدد الساعات ومطابقتها في الجداول والمحاضرات المنفذة.",
                "dynamic_tables": ["std8Annex26Table"],
            },
            {
                "key": "std8_annex27",
                "text": "تتوفر بيانات متابعة الأنشطة الصفية والتكاليف والتدريب.",
                "dynamic_tables": ["std8Annex27Table"],
            },
            {
                "key": "std8_annex28",
                "text": "تتوفر بيانات تقييم أداء أعضاء هيئة التدريس.",
                "dynamic_tables": ["std8Annex28Table"],
            },
            {
                "key": "std8_annex29",
                "text": "تتوفر نتائج رضا أعضاء هيئة التدريس.",
                "dynamic_tables": ["std8Annex29Table"],
            },
            {
                "key": "std8_annex30_education",
                "text": "تتوفر نتائج رضا الطلبة عن جودة الخدمات التعليمية.",
                "dynamic_tables": ["std8Annex30EducationTable"],
            },
            {
                "key": "std8_annex30_library",
                "text": "تتوفر نتائج رضا الطلبة عن جودة الخدمات المكتبية.",
                "dynamic_tables": ["std8Annex30LibraryTable"],
            },
            {
                "key": "std8_annex33",
                "text": "تتوفر نتائج تقييم سير العملية الامتحانية.",
                "dynamic_tables": ["std8Annex33Table"],
            },
        ],
    },
]
