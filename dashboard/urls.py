from django.urls import path

from . import reports_views
from . import views


urlpatterns = [
    # ========================================================
    # الانتقال من البوابة إلى صفحات الدخول
    # ========================================================

    path(
        "gateway/system-login/",
        views.gateway_system_login,
        name="gateway_system_login",
    ),

    path(
        "gateway/admin-login/",
        views.gateway_admin_login,
        name="gateway_admin_login",
    ),

    # ========================================================
    # الصفحة الرئيسية بعد تسجيل الدخول
    # الرابط: /home/
    # ========================================================

    path(
        "home/",
        views.home,
        name="home",
),

    # ========================================================
    # تسجيل الدخول والخروج
    # ========================================================

    path(
        "login/",
        views.system_login_view,
        name="system_login",
    ),

    path(
        "logout/",
        views.system_logout_view,
        name="system_logout",
    ),

    # ========================================================
    # إدخال بيانات وشواهد المعايير
    # ========================================================

    path(
        "data-entry/",
        views.data_entry,
        name="data_entry",
    ),

    path(
        "data-entry/delete-file/<int:file_id>/",
        views.delete_evaluation_file,
        name="delete_evaluation_file",
    ),

    path(
        "data-entry/create-from-template/",
        views.create_evaluation_from_template,
        name="create_evaluation_from_template",
    ),

    
    # ========================================================
    # التقارير
    # ========================================================

    path(
        "reports/",
        reports_views.reports,
        name="reports",
    ),

    path(
        "reports/export-log/<int:log_id>/delete/",
        reports_views.delete_report_export_log,
        name="delete_report_export_log",
    ),

    path(
        "reports/export-excel/",
        reports_views.export_reports_excel,
        name="export_reports_excel",
    ),

    path(
        "reports/export-pdf/",
        reports_views.export_reports_pdf,
        name="export_reports_pdf",
    ),

    # ========================================================
    # إدارة النظام
    # ========================================================

    path(
        "system-management/",
        views.system_management,
        name="system_management",
    ),
]