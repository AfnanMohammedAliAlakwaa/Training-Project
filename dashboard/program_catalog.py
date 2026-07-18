from django.apps import apps


DEFAULT_COLLEGE_NAME = "غير محدد"
DEFAULT_START_YEAR = 2007


def _has_field(model, field_name):
    return any(
        field.name == field_name
        for field in model._meta.get_fields()
    )


def _safe_text(value, default=""):
    if value is None:
        return default

    value = str(value).strip()

    if value.lower() in {
        "",
        "none",
        "null",
        "nan",
    }:
        return default

    return value


def get_program_options():
    """
    المصدر الموحد لقوائم البرامج في النظام.

    يقرأ مباشرة من:
        programs.Program

    وهو نفس الجدول الذي تتم إدارته من لوحة الإدارة.
    """

    ProgramModel = apps.get_model(
        "programs",
        "Program",
    )

    queryset = ProgramModel.objects.all()

    # عرض البرامج النشطة فقط إذا كان الحقل موجودًا.
    if _has_field(ProgramModel, "is_active"):
        queryset = queryset.filter(
            is_active=True
        )

    elif _has_field(ProgramModel, "active"):
        queryset = queryset.filter(
            active=True
        )

    # تحميل الكلية والقسم دون استعلامات إضافية.
    if _has_field(ProgramModel, "department"):
        department_field = ProgramModel._meta.get_field(
            "department"
        )

        DepartmentModel = (
            department_field.remote_field.model
        )

        if _has_field(DepartmentModel, "college"):
            queryset = queryset.select_related(
                "department__college"
            )
        else:
            queryset = queryset.select_related(
                "department"
            )

    ordering_fields = []

    for field_name in (
        "name",
        "specialization",
        "start_year",
        "id",
    ):
        if _has_field(ProgramModel, field_name):
            ordering_fields.append(field_name)

    if ordering_fields:
        queryset = queryset.order_by(
            *ordering_fields
        )

    options = []
    seen = set()

    for program in queryset:
        name = _safe_text(
            getattr(program, "name", "")
        )

        if not name:
            continue

        specialization = _safe_text(
            getattr(
                program,
                "specialization",
                "",
            )
        )

        if specialization in {
            "لا يوجد",
            "غير محددة",
            "-",
        }:
            specialization = ""

        display_name = name

        if specialization:
            display_name = (
                f"{name} - {specialization}"
            )

        normalized_key = " ".join(
            display_name.lower().split()
        )

        if normalized_key in seen:
            continue

        seen.add(normalized_key)

        start_year = getattr(
            program,
            "start_year",
            None,
        )

        if not start_year:
            start_year = DEFAULT_START_YEAR

        college_name = DEFAULT_COLLEGE_NAME

        department = getattr(
            program,
            "department",
            None,
        )

        if department:
            college = getattr(
                department,
                "college",
                None,
            )

            if college:
                college_name = _safe_text(
                    getattr(college, "name", ""),
                    DEFAULT_COLLEGE_NAME,
                )

        options.append(
            {
                "id": program.pk,
                "name": display_name,
                "value": display_name,
                "college": college_name,
                "start_year": int(start_year),
            }
        )

    return options