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
        "routines", "일일루틴", "화면별로 AI 에게 하루 양을 맡기고(PC 에서 실행 · 전체 실행 · 추가 실행) 쌓인 결과를 보는 곳", "routines:index", "refresh", "#0f766e",
        children=(
            Menu("routine_topics", "커스텀 글쓰기", "사이트별 소재·고정 주제를 골라 편수만큼 더 쓰는 곳", "routines:topics", "calendar"),
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
        ),
    ),
    Menu(
        "blog", "블로그·카페", "카테고리별 소재·템플릿·글과 게시 기록", "blog:list", "file", "#2f6bd8",
        listing=False,  # '블로그·카페 리스트' 중메뉴는 뺐다 (2026-10-16 사용자)
        children=(
            # 2026-10-22 사용자: 운영 · (예전) 글 관리는 메뉴에서 뺀다 (주소는 남는다). 모니터링은 새로 — 일자별 발행 수 · 발행 완료 자동 처리.
            # 글 보기 → '글 관리', 카테고리 관리 → '카테고리 관리'. 변환은 글 관리(검토글·발행예정글)에서 한다.
            # 2026-10-23 사용자: 모니터링이 맨 위 (운영 대시보드 — 확인할 것 · 사이트별 파이프라인 · 발행 실적 · 일일루틴).
            # 글 관리 아래 소메뉴: 임시·검토글 · 발행예정글(날짜 정해 두고 그날 쓰는 화면) · 게시글 관리(발행 완료) · 카테고리 관리 · 사이트별 템플릿.
            # 글 관리 이름 줄은 memorily 티스토리처럼 누르면 접고 펴기만 한다 (2026-10-23 사용자: 둘이 다르게 움직이면 이상하다).
            # 그래서 이름 줄의 주소는 첫 소메뉴(임시·검토글)와 같게 둔다 (같으면 이름 줄이 링크가 아니다, base.html).
            # 통계현황 (2026-10-23 사용자): 모니터링 위. 사이트별 방문자 · 공감 · 댓글 추이 (blog_ops/stats.py)
            Menu("blog_stats", "통계현황", "사이트별 방문자 · 공감 · 댓글 추이 (7·30·90일)", "blog_ops:stats", "list"),
            Menu("blog_ops", "모니터링", "확인할 것 · 사이트별 파이프라인(임시 → 검토 → 예정) · 발행 실적 · 일일루틴", "blog_ops:index", "check-list"),
            Menu("posts_hub", "글 관리", "임시글 → 검토글 → 발행예정글. 카테고리 넣기 · 변환 · 발행까지", "posts:view", "file", children=(
                Menu("posts_view", "임시·검토글", "원고가 들어오는 임시글과 손본 검토글. 한 건씩 보며 검토글 → 발행예정글로", "posts:view", "edit"),
                Menu("posts_planned", "발행예정글", "발행 예정일을 정하고 그날 각 블로그에 올릴 글을 보는 곳", "posts:planned", "calendar"),
                Menu("posts_published", "게시글 관리", "발행 완료한 글을 사이트 › 카테고리별로", "posts:published", "check-list"),
                Menu("blog_types", "카테고리 관리", "사이트 카테고리에 글 넣기, 글 분류 고치기", "blog_types:index", "tag"),
                Menu("site_templates", "사이트별 템플릿", "사이트·카테고리마다 글쓰기·변환 컨셉과 규칙", "site_templates:index", "layers"),
            )),
            # memorily 티스토리 (2026-10-21 사용자): 중메뉴 아래 소메뉴 — 블로그 자동화(예전 'memorily 연재') · 애니 총정리
            # · 분기별 애니 추천 및 후기 (2026-10-23 사용자: 분기 방영작에서 본 것을 골라 평점·감상을 적는 글감 화면)
            Menu("memorily_tistory", "memorily 티스토리", "memorily 티스토리에 쓰는 연재와 애니 정리 글", "series:index", "book", children=(
                Menu("series", "블로그 자동화", "AI 와 블로그 자동화를 만든 과정을 회차로 나눠 쓰는 곳", "series:index", "book"),
                Menu("anime", "애니 총정리", "애니↔만화 환산기 글을 작품마다 쓰는 곳 (나루토부터)", "anime:index", "book"),
                Menu("anime_seasons", "분기별 애니 추천 및 후기", "분기 방영작에서 본 애니를 골라 평점·감상을 적어 두는 곳", "anime_seasons:index", "film"),
            )),
        ),
    ),
    Menu(
        "video", "영상 콘텐츠", "시리즈별 소재·대본과 플랫폼별 버전", "video:list", "layers", "#7c3aed"),
    # 창작콘텐츠 (2026-10-22 사용자): 상상 소재 하나를 여러 방식으로 만들어 보는 검증. 게시용이 아니다.
    Menu(
        "studio", "창작콘텐츠", "상상 소재 하나를 카툰·숏폼·글 등 여러 방식으로 만들어 비교하는 곳", "studio:index", "palette", "#b45309",
        children=(
            Menu("studio_cartoon", "인스타 카툰", "10장 카툰을 그림판·연필·깔끔 세 가지 마감으로", "studio:cartoon", "image"),
            Menu("studio_shorts", "숏폼 영상", "9:16 영상 재생 · 효과음 · 내 목소리 녹음 · MP4 저장", "studio:shorts", "film"),
            Menu("studio_thread", "쓰레드 글", "같은 소재를 글타래와 한 줄 글로", "studio:thread", "message"),
            Menu("studio_prompts", "AI 이미지 설정집", "이미지 AI 에 넘길 캐릭터·화풍·컷별 지시문", "studio:prompts", "edit"),
            Menu("studio_review", "검증 기록", "방식별로 AI 티·품질·손이 가는 정도를 따져 본 결과", "studio:review", "check-list"),
        ),
    ),
    # 일정관리 (2026-10-22 사용자): 큰 월 달력 + 고른 날 일정 + 입력·수정 폼
    Menu("schedule", "일정관리", "달력으로 일정을 보고 날짜별로 넣고 고치는 곳", "schedule:index", "calendar", "#0891b2"),
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


def walk(menus=None):
    """메뉴 트리를 위에서부터 차례로 (상위 · 중메뉴 · 소메뉴)."""
    for menu in MENUS if menus is None else menus:
        yield menu
        yield from walk(menu.children)


def menu_keys_for(app_name: str, url_name: str) -> list[str]:
    """이 화면(주소 이름)이 속한 메뉴 key 들. 권한 검사(middleware)에 쓴다.
    core 앱은 화면마다(홈·설정 등은 메뉴가 아니다), 나머지는 앱 단위로 본다. 글쓰기 두 앱은 '글 관리' 아래다."""
    app_name = {"writing": "posts", "naver_writing": "posts"}.get(app_name, app_name)
    full = f"{app_name}:{url_name}"
    keys = []
    for m in walk():
        ns = m.url_name.split(":")[0]
        if (app_name == "core" and m.url_name == full) or (app_name != "core" and ns == app_name):
            keys.append(m.key)
    return keys


def find_menu(key: str) -> Menu | None:
    """상위·하위 메뉴를 통틀어 key 로 찾는다."""
    return next((m for m in walk() if m.key == key), None)


# 대메뉴마다 있던 '논의 현황' 중메뉴는 뺐다 (2026-10-23 사용자). 논의는 진행현황(discussions) 한곳에서 본다.
# 블로그·카페 중메뉴 순서 (2026-10-23 사용자): 모니터링 · 글 관리(› 임시·검토글 · 발행예정글 · 게시글 관리 · 카테고리 관리 · 사이트별 템플릿) · memorily 티스토리.


def build_nav(active_key: str, user=None) -> list[dict]:
    """좌측 메뉴용 트리. 현재 화면이 속한 가지는 펼친 채로 내보낸다. user 를 주면 볼 수 있는 메뉴만."""
    nav = []
    for menu in get_menus(user):
        if not menu.children:
            nav.append({"menu": menu, "active": menu.key == active_key, "open": False, "children": []})
            continue
        first = (Menu(menu.key, f"{menu.title} 리스트", menu.description, menu.url_name, menu.icon, menu.color, menu.query),) if menu.listing else ()
        children = []
        for child in (*first, *menu.children):  # 중메뉴 아래 소메뉴는 이름 한 줄 + 들여 쓴 링크로 (memorily 티스토리)
            subs = [{"menu": g, "active": g.key == active_key} for g in child.children]
            # 이름 줄이 링크인가: 주소가 첫 소메뉴와 다르면 (글 관리). 같으면 이름만 (memorily 티스토리)
            link = bool(subs) and child.url != child.children[0].url
            children.append({"menu": child, "active": child.key == active_key or any(s["active"] for s in subs), "children": subs,
                             "link": link, "self_active": child.key == active_key})
        nav.append({"menu": menu, "active": False, "open": any(c["active"] for c in children), "children": children})
    return nav
