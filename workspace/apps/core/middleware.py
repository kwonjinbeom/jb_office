"""관리화면 › 메뉴 권한을 화면 접근에도 적용한다.

메뉴에 '볼 수 있는 그룹'을 정하면 그 그룹 사용자(와 슈퍼유저)만 왼쪽 메뉴에서 보고, 주소로 들어와도 403 이다.
한 화면이 여러 메뉴에 걸쳐 있으면(예: 논의 현황) 그중 하나라도 볼 수 있으면 들어간다. 메뉴가 아닌 화면(홈·설정·관리화면)은 막지 않는다.
"""
from django.core.exceptions import PermissionDenied

from .menus import _settings, allowed, menu_keys_for


class MenuPermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)
        match = getattr(request, "resolver_match", None)
        if not match or not user or not user.is_authenticated or user.is_superuser or not match.app_name:
            return None
        if match.app_name == "admin":
            return None
        keys = menu_keys_for(match.app_name, match.url_name or "")
        if not keys:
            return None
        saved = _settings()
        if any(allowed(k, user, saved) for k in keys):
            return None
        raise PermissionDenied("이 메뉴를 볼 권한이 없습니다.")


class PcAdminAutoLoginMiddleware:
    """PC(로그인 없이 쓰는 개발 모드, REQUIRE_LOGIN=False)에서는 관리화면도 따로 로그인하지 않는다 (2026-10-16 사용자).

    관리화면에 들어오면 PC 전용 관리자 계정('pc')으로 자동 로그인한다. 서버(REQUIRE_LOGIN=True)에서는 아무것도 하지 않는다 —
    서버는 앱에 로그인한 계정(관리자 권한이 있는 계정)으로 관리화면이 바로 열린다.
    """

    USERNAME = "pc"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings
        from django.urls import reverse

        if not settings.REQUIRE_LOGIN and not request.user.is_authenticated and request.path.startswith(reverse("admin:index")):
            from django.contrib.auth import get_user_model, login

            user, created = get_user_model().objects.get_or_create(
                username=self.USERNAME, defaults={"is_staff": True, "is_superuser": True})
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return self.get_response(request)
