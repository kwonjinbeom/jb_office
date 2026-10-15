"""메뉴 레지스트리.

새 메뉴(앱)를 추가할 때는 여기에 항목 하나만 넣으면 홈 카드와 좌측 내비게이션에 함께 나타난다.
- key: 앱 이름(urls.py 의 app_name)과 같게 둔다. 현재 메뉴 강조에 쓴다.
- url_name: reverse() 가능한 이름.
- icon: templates/includes/icons.html 의 symbol 이름 (i-<icon>). 없는 아이콘은 그 파일에 추가한다.
- color: 홈 카드의 아이콘 색. 사무적인 톤의 색만 쓴다.

하위 메뉴(트리)
- children 에 Menu 를 넣으면 좌측 메뉴에서 그 항목 아래에 펼쳐진다. 상위 메뉴를 누르거나 옆 화살표를 누르면 보인다.
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
            Menu("writing", "티스토리 글쓰기", "임시 템플릿 → 검토 템플릿 → 포스트 관리", "writing:list", "edit"),
            Menu("naver_writing", "네이버 글쓰기", "임시 템플릿 → 검토 템플릿 → 포스트 관리", "naver_writing:list", "edit"),
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
        children = [{"menu": child, "active": child.key == active_key} for child in menu.children]
        active = menu.key == active_key
        nav.append({"menu": menu, "active": active, "open": active or any(c["active"] for c in children), "children": children})
    return nav
