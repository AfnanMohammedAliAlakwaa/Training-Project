from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from .middleware import get_client_ip, get_current_request
from .models import ActivityLog


# الموديلات التي نريد تسجيل حذفها
# مهم: EvaluationFile عندك غالبًا داخل dashboard وليس evaluations
AUDITED_DELETE_MODELS = {
    ("programs", "program"): "البرامج الأكاديمية",
    ("dashboard", "evaluationfile"): "ملفات التقييم",
}


def get_actor_from_request():
    request = get_current_request()

    if not request:
        return None

    user = getattr(request, "user", None)

    if user and user.is_authenticated:
        return user

    return None


def safe_object_repr(instance):
    try:
        return str(instance)[:255]
    except Exception:
        return f"{instance._meta.verbose_name} رقم {instance.pk}"


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ActivityLog.objects.create(
        user=user,
        action="login",
        section="تسجيل الدخول",
        standard_label="",
        model_name="حساب مستخدم",
        object_id=str(user.pk),
        object_repr=f"تسجيل دخول: {user.username}",
        changes="تم تسجيل الدخول إلى النظام.",
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
        url=request.get_full_path(),
    )


@receiver(pre_delete)
def log_delete(sender, instance, **kwargs):
    meta = instance._meta
    model_key = (meta.app_label, meta.model_name)

    if model_key not in AUDITED_DELETE_MODELS:
        return

    request = get_current_request()
    user = get_actor_from_request()

    if not user:
        return

    current_url = request.get_full_path() if request else ""
    from_admin = current_url.startswith("/admin/")

    ActivityLog.objects.create(
        user=user,
        action="delete",
        section=AUDITED_DELETE_MODELS[model_key],
        standard_label="",
        model_name=meta.verbose_name,
        object_id=str(instance.pk or ""),
        object_repr=safe_object_repr(instance),
        changes="تم حذف السجل من لوحة الأدمن." if from_admin else "تم حذف السجل من النظام الرئيسي.",
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000] if request else "",
        url=current_url,
    )