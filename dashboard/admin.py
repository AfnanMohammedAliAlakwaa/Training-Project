from django.contrib import admin
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
)


@admin.register(AcademicProgram)
class AcademicProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "specialization", "start_year", "is_active")
    search_fields = ("name", "specialization")
    list_filter = ("is_active",)


@admin.register(EvaluationFile)
class EvaluationFileAdmin(admin.ModelAdmin):
    list_display = ("program", "academic_year", "status", "created_at", "updated_at")
    search_fields = ("program__name", "program__specialization", "academic_year")
    list_filter = ("status", "academic_year")


@admin.register(QualityStandard)
class QualityStandardAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "weight", "is_active")
    search_fields = ("title",)
    list_filter = ("is_active",)
    ordering = ("number",)


@admin.register(StandardEntry)
class StandardEntryAdmin(admin.ModelAdmin):
    list_display = (
        "evaluation_file",
        "standard",
        "completion_status",
        "completion_percentage",
        "saved_as_draft",
        "updated_at",
    )
    search_fields = (
        "evaluation_file__program__name",
        "evaluation_file__academic_year",
        "standard__title",
    )
    list_filter = ("completion_status", "saved_as_draft", "standard")


@admin.register(EvidenceAttachment)
class EvidenceAttachmentAdmin(admin.ModelAdmin):
    list_display = ("title", "standard_entry", "uploaded_at")
    search_fields = ("title",)


@admin.register(StudentLevelCount)
class StudentLevelCountAdmin(admin.ModelAdmin):
    list_display = ("evaluation_file", "level_name", "male_count", "female_count", "total_count")
    search_fields = ("evaluation_file__program__name", "level_name")


@admin.register(GraduateRecord)
class GraduateRecordAdmin(admin.ModelAdmin):
    list_display = ("evaluation_file", "academic_year", "graduates_count", "cumulative_gpa")
    search_fields = ("evaluation_file__program__name", "academic_year")


@admin.register(CourseRecord)
class CourseRecordAdmin(admin.ModelAdmin):
    list_display = ("evaluation_file", "course_name", "course_code", "credit_hours", "level", "has_specification")
    search_fields = ("course_name", "course_code", "evaluation_file__program__name")
    list_filter = ("has_specification", "level")


@admin.register(FacultyMemberRecord)
class FacultyMemberRecordAdmin(admin.ModelAdmin):
    list_display = ("evaluation_file", "name", "qualification", "academic_rank", "employment_type", "teaching_load")
    search_fields = ("name", "evaluation_file__program__name")
    list_filter = ("qualification", "academic_rank", "employment_type")


@admin.register(InfrastructureRecord)
class InfrastructureRecordAdmin(admin.ModelAdmin):
    list_display = ("evaluation_file", "facility_type", "count", "area")
    search_fields = ("facility_type", "evaluation_file__program__name")


@admin.register(LibrarySourceRecord)
class LibrarySourceRecordAdmin(admin.ModelAdmin):
    list_display = ("evaluation_file", "source_type", "title", "count", "release_year")
    search_fields = ("source_type", "title", "evaluation_file__program__name")


@admin.register(EducationProcessRecord)
class EducationProcessRecordAdmin(admin.ModelAdmin):
    list_display = ("evaluation_file", "item", "status", "value", "evidence")
    search_fields = ("item", "evaluation_file__program__name")