from django.conf import settings
from django.utils import timezone

from . import gitstate
from .menus import get_menus


def navigation(request):
    """모든 템플릿에 메뉴 목록, 현재 활성 메뉴 키, 오늘 날짜, 배포 정보를 넣는다."""
    match = getattr(request, "resolver_match", None)
    active = match.app_name if match else ""
    return {
        "MENUS": get_menus(),
        "ACTIVE_MENU": active or "home",
        "today": timezone.localdate(),
        "DEPLOY_INFO": {
            "head": gitstate.head_short(),
            "last": gitstate.load_deploy_state(),
            "is_server": settings.IS_SERVER,
        },
    }
