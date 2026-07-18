from django.urls import path
from . import views

urlpatterns = [
    path("evaluation/", views.evaluation_page, name="evaluation"),
    path("analysis/", views.analysis_page, name="analysis"),
]