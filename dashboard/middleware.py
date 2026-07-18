from threading import local
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect


_thread_locals = local()


def get_current_request():
    return getattr(_thread_locals, "request", None)


def get_client_ip(request):
    if not request:
        return None

    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


class CurrentUserMiddleware:
    """
    يحفظ الطلب الحالي حتى نعرف من المستخدم الذي أضاف أو عدل أو حذف.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request

        try:
            return self.get_response(request)
        finally:
            _thread_locals.request = None


class MainSystemLoginRequiredMiddleware:
    EXEMPT_PREFIXES = (
        "/login/",
        "/logout/",
        "/admin/",
        "/static/",
        "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        if request.user.is_authenticated:
            return self.get_response(request)

        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        query_string = urlencode({"next": request.get_full_path()})
        return redirect(f"{settings.LOGIN_URL}?{query_string}")