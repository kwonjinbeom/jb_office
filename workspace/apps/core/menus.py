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
"""
from dataclasses import dataclass

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

    @property
    def url(self) -> str:
        return reverse(self.url_name) + self.query


MENUS: list[Menu] = [
    Menu(
        "routines", "일일루틴", "화면별로 AI 에게 하루 양을 맡기고(로컬·클라우드) 쌓인 결과를 보는 곳", "routines:index", "refresh", "#0f766e",
        children=(
            Menu("routine_prompts", "프롬프트 관리", "루틴마다 로컬·클라우드 프롬프트와 그 프롬프트가 보는 md", "routines:prompts", "edit"),
        ),
    ),
    Menu(
        "daily_ideas", "일일 아이디어", "날짜별로 조사한 후보를 비교하고 필요한 것만 담는 곳", "daily_ideas:list", "sparkles", "#334155",
        children=(
            Menu("daily_standard", "검색 표준", "아이디어를 찾을 때 주는 조건을 쓰고 버전으로 남기는 곳", "daily_ideas:standard", "edit"),
            Menu("daily_ideas_discussions", "논의 현황", "일일 아이디어에서 정한 것과 다음 행동", "discussions:list", "message", query="?area=daily_ideas"),
        ),
    ),
    Menu(
        "ideas", "내 아이디어", "내가 고른 후보를 단계별로 실제 작업으로 바꾸는 곳", "ideas:list", "bulb", "#2f6bd8",
        children=(
            Menu("ideas_discussions", "논의 현황", "내 아이디어에서 정한 것과 다음 행동", "discussions:list", "message", query="?area=ideas"),
        ),
    ),
    Menu(
        "blog", "블로그·카페", "카테고리별 소재·템플릿·글과 게시 기록", "blog:list", "file", "#2f6bd8",
        children=(
            Menu("blog_rules", "운영", "사이트별 컨셉·발행·임시저장 현황과 체크", "blog_rules:index", "check-list"),
            Menu("blog_ops", "모니터링", "이번 주 발행 현황, 발행 계획, RSS", "blog_ops:index", "calendar"),
            Menu("posts", "글 관리", "티스토리·네이버 글: 임시 템플릿 → 검토 템플릿 → 포스트 관리, 글 분류별", "posts:index", "edit"),
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


def get_menus() -> list[Menu]:
    return MENUS


def find_menu(key: str) -> Menu | None:
    """상위·하위 메뉴를 통틀어 key 로 찾는다."""
    for menu in MENUS:
        if menu.key == key:
            return menu
        for child in menu.children:
            if child.key == key:
                return child
    return None


def build_nav(active_key: str) -> list[dict]:
    """좌측 메뉴용 트리. 현재 화면이 속한 가지는 펼친 채로 내보낸다."""
    nav = []
    for menu in MENUS:
        if not menu.children:
            nav.append({"menu": menu, "active": menu.key == active_key, "open": False, "children": []})
            continue
        listing = Menu(menu.key, f"{menu.title} 리스트", menu.description, menu.url_name, menu.icon, menu.color, menu.query)
        children = [{"menu": child, "active": child.key == active_key} for child in (listing, *menu.children)]
        nav.append({"menu": menu, "active": False, "open": any(c["active"] for c in children), "children": children})
    return nav
