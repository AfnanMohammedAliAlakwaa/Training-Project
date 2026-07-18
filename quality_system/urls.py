"""
URL configuration for quality_system project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from dashboard.views import login_gateway


urlpatterns = [
    # بوابة الدخول الموحد
    path(
        "",
        login_gateway,
        name="login_gateway",
    ),

    # لوحة إدارة Django
    path(
        "admin/",
        admin.site.urls,
    ),

    # تطبيق التقييم
    path(
        "",
        include("evaluations.urls"),
    ),

    # تطبيق خطط التحسين
    path(
        "",
        include("improvements.urls"),
    ),

    # لوحة النظام
    path(
        "",
        include("dashboard.urls"),
    ),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )