"""메뉴 레지스트리.

새 메뉴(앱)를 추가할 때는 여기에 항목 하나만 넣으면 홈 카드와 좌측 내비게이션에 함께 나타난다.
- key: 앱 이름(urls.py 의 app_name)과 같게 둔다. 현재 메뉴 강조에 쓴다.
- url_name: reverse() 가능한 이름.
- icon: templates/includes/icons.html 의 symbol 이름 (i-<icon>). 없는 아이콘은 그 파일에 추가한다.
- color: 홈 카드의 아이콘 색. 사무적인 톤의 색만 쓴다.

하위 메뉴(트리)
- children 에 Menu 를 넣으면 좌측 메뉴에서 그 항목 아래에 펼쳐진다. 하위가 있는 상위 메뉴는 펼치기만 하고 이동하지 않는다
  (2026-10-16 사용자). 상위 메뉴의 원래 화면은 맨 위 중메뉴 '<상위 메뉴명> 리스트' 로 들어간다 (build_nav 가 만든다).
- 하위 메뉴의 key 는 앱 이름과 달라도 된다. 그 화면의 뷰에서 `request.nav_key = "<key>"` 를 넣으면 그 항목이 강조된다
  (예: apps/discussions/views.py 의 _nav). 넣지 않으면 앱 이름과 같은 key 가 강조된다.
- query: 같은 화면을 조건만 달리해 여는 하위 메뉴에 쓴다 (예: "?area=blog").
- listing=False: '<상위 메뉴명> 리스트' 를 만들지 않는다. 하위 메뉴들이 곧 그 묶음의 화면일 때 (예: 아이디어 = 일일 + 내 아이디어).

관리화면 › 메뉴 권한(admin, apps/core/admin.py)에서 이름·순서·보이기·볼 수 있는 그룹을 고치면 MenuSetting 에 남고,
get_menus()·build_nav() 가 그 값을 입힌다. 사용자를 주면 그 사용자가 볼 수 있는 메뉴만 남긴다 (allowed).
주소·하위 구조·새 메뉴는 여기서 고친다.
"""
from dataclasses import dataclass, replace

from django.urls import reverse


@dataclass(frozen=True)
class Menu:
    key: str
    title: str
    description: str
    url_name: str
    icon: str
    color: str = "#2f6bd8"
    query: str = ""
    children: tuple["Menu", ...] = ()
    listing: bool = True

    @property
    def url(self) -> str:
        return reverse(self.url_name) + self.query


MENUS: list[Menu] = [
    Menu(
        "routines", "일일루틴", "화면별로 AI 에게 하루 양을 맡기고(매일 아침 7시 예약 · 더 하고 싶으면 추가 실행) 쌓인 결과를 보는 곳", "routines:index", "refresh", "#0f766e",
        children=(
            Menu("routine_extra", "추가 실행", "아침 예약과 별도로 글·아이디어를 더 돌리고, 글쓰기 아침 분량을 고르는 곳", "routines:extra_page", "plus"),
            Menu("routine_prompts", "프롬프트 관리", "루틴마다 프롬프트와 그 프롬프트가 보는 md", "routines:prompts", "edit"),
        ),
    ),
    # 일일 아이디어 + 내 아이디어 (2026-10-16 사용자). 검색 표준은 일일루틴 › 프롬프트 관리의 자료로 옮겨 메뉴에서 뺐다.
    Menu(
        "idea_hub", "아이디어", "날짜별로 조사한 후보(일일)와 내가 고른 아이디어, 그 논의", "daily_ideas:list", "sparkles", "#334155",
        listing=False,
        children=(
            Menu("daily_ideas", "일일 아이디어", "날짜별로 조사한 후보를 비교하고 필요한 것만 담는 곳", "daily_ideas:list", "sparkles"),
            Menu("ideas", "내 아이디어", "내가 고른 후보를 단계별로 실제 작업으로 바꾸는 곳", "ideas:list", "bulb"),
            Menu("idea_discussions", "논의 현황", "아이디어(일일·내 아이디어)에서 정한 것과 다음 행동", "discussions:list", "message", query="?area=idea"),
        ),
    ),
    Menu(
        "blog", "블로그·카페", "카테고리별 소재·템플릿·글과 게시 기록", "blog:list", "file", "#2f6bd8",
        listing=False,  # '블로그·카페 리스트' 중메뉴는 뺐다 (2026-10-16 사용자)
        children=(
            Menu("blog_rules", "운영", "사이트별 컨셉·발행·임시저장 현황과 체크", "blog_rules:index", "check-list"),
            Menu("blog_ops", "모니터링", "이번 주 발행 현황, 발행 계획, RSS", "blog_ops:index", "calendar"),
            Menu("posts", "글 관리", "티스토리·네이버 글: 임시글 → 검토글 → 발행예정글, 글 분류별", "posts:index", "edit"),
            Menu("blog_types", "글 매핑 관리", "사이트 카테고리에 글 넣기, 글 분류 고치기", "blog_types:index", "tag"),
            Menu("site_templates", "사이트별 템플릿", "사이트 컨셉·플랫폼 포맷에 맞게 글 변환", "site_templates:index", "layers"),
            Menu("blog_discussions", "논의 현황", "블로그·카페에서 정한 것과 다음 행동", "discussions:list", "message", query="?area=blog"),
        ),
    ),
    Menu(
        "video", "영상 콘텐츠", "시리즈별 소재·대본과 플랫폼별 버전", "video:list", "layers", "#7c3aed",
        children=(
            Menu("video_discussions", "논의 현황", "영상 콘텐츠에서 정한 것과 다음 행동", "discussions:list", "message", query="?area=video"),
        ),
    ),
    Menu("discussions", "진행현황", "전체 주제별 현재 핵심과 다음 행동을 한곳에서", "discussions:list", "list", "#0f766e"),
    Menu("memos", "메모", "떠오른 생각, 참고 사항을 빠르게 기록", "memos:list", "memo", "#64748b"),
    Menu("trash", "휴지통", "모든 화면의 삭제 항목 · 7일간 복원", "core:trash", "trash", "#64748b"),
    Menu("docs", "문서", "시장조사 폴더의 문서를 화면에서 읽기 (읽기 전용)", "docs:list", "book", "#475569"),
]


def _settings() -> dict:
    from django.db import DatabaseError

    from .models import MenuSetting
    try:
        out = {}
        for s in MenuSetting.objects.prefetch_related("groups"):
            s.group_ids = {g.pk for g in s.groups.all()}
            out[s.key] = s
        return out
    except DatabaseError:  # migrate 전
        return {}


def _user_groups(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    if not hasattr(user, "_menu_group_ids"):
        user._menu_group_ids = set(user.groups.values_list("pk", flat=True))
    return user._menu_group_ids


def allowed(key, user, saved=None) -> bool:
    """이 사용자가 이 메뉴를 볼 수 있나. 그룹을 안 정한 메뉴는 모두, 슈퍼유저는 늘."""
    if user is None or getattr(user, "is_superuser", False):
        return True
    saved = _settings() if saved is None else saved
    s = saved.get(key)
    if s is None or not getattr(s, "group_ids", None):
        return True
    return bool(s.group_ids & (_user_groups(user) or set()))


def _apply(menus, saved, keep_hidden=False, user=None):
    """기본 순서(코드) 위에 화면에서 고친 순서·이름·숨김을 입힌다. user 를 주면 볼 수 없는 메뉴를 뺀다."""
    out = []
    for i, menu in enumerate(menus):
        s = saved.get(menu.key)
        if s and s.hidden and not keep_hidden:
            continue
        if not allowed(menu.key, user, saved):
            continue
        menu = replace(menu, title=(s.title if s and s.title else menu.title),
                       children=tuple(_apply(menu.children, saved, keep_hidden, user)))
        out.append(((s.order if s else 1000 + i), i, menu))  # 화면에서 아직 안 정한 메뉴(새 메뉴)는 뒤로
    return [m for _, _, m in sorted(out, key=lambda t: (t[0], t[1]))]


def get_menus(user=None) -> list[Menu]:
    """화면에 보이는 메뉴 (메뉴 권한에서 고친 이름·순서·숨김을 입히고, user 를 주면 볼 수 있는 것만)."""
    return _apply(MENUS, _settings(), user=user)


def all_menus() -> list[Menu]:
    """메뉴 권한 화면용: 숨긴 것도 포함해 순서·이름만 입힌 목록."""
    return _apply(MENUS, _settings(), keep_hidden=True)


def menu_keys_for(app_name: str, url_name: str) -> list[str]:
    """이 화면(주소 이름)이 속한 메뉴 key 들. 권한 검사(middleware)에 쓴다.
    core 앱은 화면마다(홈·설정 등은 메뉴가 아니다), 나머지는 앱 단위로 본다. 글쓰기 두 앱은 '글 관리' 아래다."""
    app_name = {"writing": "posts", "naver_writing": "posts"}.get(app_name, app_name)
    full = f"{app_name}:{url_name}"
    keys = []
    for menu in MENUS:
        for m in (menu, *menu.children):
            ns = m.url_name.split(":")[0]
            if (app_name == "core" and m.url_name == full) or (app_name != "core" and ns == app_name):
                keys.append(m.key)
    return keys


def find_menu(key: str) -> Menu | None:
    """상위·하위 메뉴를 통틀어 key 로 찾는다."""
    for menu in MENUS:
        if menu.key == key:
            return menu
        for child in menu.children:
            if child.key == key:
                return child
    return None


def build_nav(active_key: str, user=None) -> list[dict]:
    """좌측 메뉴용 트리. 현재 화면이 속한 가지는 펼친 채로 내보낸다. user 를 주면 볼 수 있는 메뉴만."""
    nav = []
    for menu in get_menus(user):
        if not menu.children:
            nav.append({"menu": menu, "active": menu.key == active_key, "open": False, "children": []})
            continue
        first = (Menu(menu.key, f"{menu.title} 리스트", menu.description, menu.url_name, menu.icon, menu.color, menu.query),) if menu.listing else ()
        children = [{"menu": child, "active": child.key == active_key} for child in (*first, *menu.children)]
        nav.append({"menu": menu, "active": False, "open": any(c["active"] for c in children), "children": children})
    return nav
