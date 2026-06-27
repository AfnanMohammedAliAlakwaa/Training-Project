from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # إدخال بيانات وشواهد المعايير
    path('data-entry/', views.data_entry, name='data_entry'),
    
    path(
    'data-entry/delete-file/<int:file_id>/',
    views.delete_evaluation_file,
    name='delete_evaluation_file'
),

    # التقييم
    path('evaluation/', views.evaluation, name='evaluation'),

    # التحليل
    path('analysis/', views.analysis, name='analysis'),

    # خطط التحسين
    path('improvement-plans/', views.improvement_plans, name='improvement_plans'),

    # التقارير
    path('reports/', views.reports, name='reports'),

    # إدارة النظام
    path('system-management/', views.system_management, name='system_management'),
]