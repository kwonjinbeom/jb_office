from .menus import get_menus


def navigation(request):
    """모든 템플릿에 메뉴 목록과 현재 활성 메뉴 키를 넣는다."""
    match = getattr(request, "resolver_match", None)
    active = match.app_name if match else ""
    return {"MENUS": get_menus(), "ACTIVE_MENU": active or "home"}
