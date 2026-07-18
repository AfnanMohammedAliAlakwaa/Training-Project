from django.urls import path

from . import views

urlpatterns = [
    path(
        "improvement-plans/",
        views.improvement_plans_page,
        name="improvement_plans",
    ),
    path(
        "improvement-plans/create-from-standard/",
        views.create_plan_from_standard,
        name="create_improvement_plan_from_standard",
    ),
    path(
        "improvement-plans/create-manual/",
        views.create_manual_plan,
        name="create_manual_improvement_plan",
    ),
    path(
        "improvement-plans/<int:plan_id>/status/",
        views.update_plan_status,
        name="update_improvement_plan_status",
    ),
    path(
        "improvement-plans/<int:plan_id>/update/",
        views.update_plan_details,
        name="update_improvement_plan_details",
    ),
]