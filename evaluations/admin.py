from django.contrib import admin
from .models import (
    EvaluationDomain,
    EvaluationIndicator,
    ProgramEvaluation,
    IndicatorScore,
)


class EvaluationIndicatorInline(admin.TabularInline):
    model = EvaluationIndicator
    extra = 1


@admin.register(EvaluationDomain)
class EvaluationDomainAdmin(admin.ModelAdmin):
    list_display = ("order", "name", "weight")
    list_editable = ("weight",)
    ordering = ("order",)
    inlines = [EvaluationIndicatorInline]


@admin.register(EvaluationIndicator)
class EvaluationIndicatorAdmin(admin.ModelAdmin):
    list_display = ("order", "domain", "short_text", "is_active")
    list_filter = ("domain", "is_active")
    search_fields = ("text",)

    def short_text(self, obj):
        return obj.text[:80]

    short_text.short_description = "المؤشر"


class IndicatorScoreInline(admin.TabularInline):
    model = IndicatorScore
    extra = 0


@admin.register(ProgramEvaluation)
class ProgramEvaluationAdmin(admin.ModelAdmin):
    list_display = ("program", "academic_year", "status", "created_at")
    list_filter = ("academic_year", "status", "program__department")
    search_fields = ("program__name",)
    inlines = [IndicatorScoreInline]


@admin.register(IndicatorScore)
class IndicatorScoreAdmin(admin.ModelAdmin):
    list_display = ("evaluation", "indicator", "score")
    list_filter = ("score", "indicator__domain")
    search_fields = ("indicator__text", "evaluation__program__name")