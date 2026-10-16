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
