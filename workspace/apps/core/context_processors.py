from django.conf import settings
from django.utils import timezone

from . import gitstate
from .menus import build_nav, get_menus


def _asset_version() -> str:
    """app.css·app.js 의 수정 시각. 주소 뒤 ?v= 로 붙여, 파일이 바뀌면 폰 브라우저도 새로 받게 한다."""
    latest = 0
    for rel in ("css/app.css", "js/app.js", "js/editor.js", "js/naver-editor.js", "js/trash.js"):
        try:
            latest = max(latest, int((settings.BASE_DIR / "static" / rel).stat().st_mtime))
        except OSError:
            pass
    return str(latest)


def navigation(request):
    """모든 템플릿에 메뉴 목록, 현재 활성 메뉴 키, 오늘 날짜, 배포 정보를 넣는다."""
    match = getattr(request, "resolver_match", None)
    # 뷰가 request.nav_key 로 하위 메뉴를 지정했으면 그것을, 아니면 앱 이름을 현재 메뉴로 본다.
    active = getattr(request, "nav_key", "") or (match.app_name if match else "")
    # 티스토리·네이버 글쓰기의 글 보기·쓰기 화면은 합친 메뉴 '글 관리' 아래에 있다
    active = {"writing": "posts", "naver_writing": "posts"}.get(active, active)
    try:
        status = gitstate.deploy_status()
    except Exception:  # git 이 없거나 저장소 밖이어도 화면은 떠야 한다
        status = None
    return {
        "MENUS": get_menus(getattr(request, "user", None)),
        "NAV": build_nav(active, getattr(request, "user", None)),
        "ACTIVE_MENU": active or "home",
        "today": timezone.localdate(),
        "ASSET_VER": _asset_version(),
        "DEPLOY_INFO": {
            "status": status,
            "last": gitstate.load_deploy_state(),
            "is_server": settings.IS_SERVER,
        },
    }
