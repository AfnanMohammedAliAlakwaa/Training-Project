from django.contrib import admin
from .models import College, Department, AcademicYear, Program


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "college")
    list_filter = ("college",)
    search_fields = ("name", "college__name")


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "program_type", "program_manager")
    list_filter = ("department__college", "department", "program_type")
    search_fields = ("name", "program_manager", "department__name")