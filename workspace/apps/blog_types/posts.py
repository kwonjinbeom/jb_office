"""글 관리: 모든 글을 한 화면에서 (2026-10-16 사용자). 편집기(티스토리·네이버) 구분은 쓰지 않는다 —
사이트·플랫폼에 맞추는 건 사이트별 템플릿의 변환에서 한다. 새 글은 한 표(writing.Post)에 만든다.

왼쪽은 카테고리 관리와 같은 글 분류 트리(모든 글 › 대분류 · 미분류 › 카테고리 › 타입 › 하위, 티스토리·네이버 나눔 없음), 오른쪽은 임시글 → 검토글 →
발행예정글 탭과 그 단계의 글. 트리에서 고르면 그 아래 글만 보인다. 글 보기·쓰기·상태 바꾸기·옮기기는 각 글쓰기 앱의 주소를 그대로 쓴다
(글은 여전히 writing.Post / naver_writing.Post 두 표에 있다).

주소: ?stage=temp|review|post|done &sel=g1|c3|t5|s9|u &q=검색어 &today=1(오늘 만든 글만) &custom=1(커스텀 글만) &site=사이트 이름
     &view=list(임시글·검토글을 목록으로)

발행예정글 (2026-10-22 사용자): 사이트로 거르고, 줄마다 발행 예정일(planned_on)을 정해 그 날짜 순으로 늘어놓는다.

중메뉴 셋 (2026-10-23 사용자): 글 관리(임시글 → 검토글 → 발행예정글 탭, 그대로) · 발행예정글(planned: 매일 보고 각 블로그에
쓰는 화면이라 두 표를 크게) · 게시글 관리(published: 발행 완료한 글, 사이트 → 카테고리 → 발행일 순). 게시글 관리는 글 관리의 탭에서 뺐다.

커스텀 (2026-10-22 사용자): 일일루틴 하루 분량(11편)이 아닌 글 — 커스텀 글쓰기의 고정 주제·추가 실행·따로 요청한 글.
원고의 `고정주제:`·`커스텀:` 줄로 가린다 (writing.Post.custom).

보기 (2026-10-22 사용자): 임시글·검토글은 기본이 한 건씩 보기(글 화면 + 왼쪽 글 목록), '목록'으로 바꾸면 체크해서 한꺼번에
옮기기·삭제하는 표. 발행예정글은 늘 표.

글을 누르면 글 보기(각 글쓰기 앱의 detail)로 간다. 글 보기 왼쪽에는 분류 트리 대신 같은 조건(단계·분류·검색·오늘)의
글 목록을 보여 준다 (post_list_for). 조건은 주소에 그대로 실어 보낸다 (2026-10-17 사용자).

단계별 칸 (2026-10-17 사용자): 임시글은 사이트(읽기)·내용, 검토글은 사이트 고르기, 발행예정글은 사이트 고르기 ·
넣은 곳(사이트 › 카테고리) · 변환 · 발행(미발행/발행 완료, 한 건씩 또는 체크한 것 한꺼번에). 작성 상태는 글 보기에서.
"""
from collections import Counter
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Prefetch, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import classify, sites, transfer
from .views import _find, _path, _placements_qs, _site_groups

# 게시글 관리 (2026-10-22 사용자): 발행 완료한 발행예정글 (글의 stage 는 그대로 post).
# 2026-10-23 사용자: 글 관리의 탭에서 빼 중메뉴로 (posts:published). 글 관리 탭은 TAB_KEYS 셋.
STAGES = [("temp", "임시글"), ("review", "검토글"), ("post", "발행예정글"), ("done", "게시글 관리")]
STAGE_KEYS = [k for k, _ in STAGES]
TAB_KEYS = ("temp", "review", "post")
TABLE_STAGES = ("post", "done")  # 늘 표로 보는 탭 (분류 트리·한 건씩 보기 없음)
CLASS_KINDS = {"section", "category", "type", "sub", "unclassified"}


def _filtered(writer, kind, obj, q, today=False, custom=False, site=""):
    qs = classify.post_model(writer).objects.all()
    if site:
        qs = qs.filter(target=site)
    if kind in CLASS_KINDS:
        qs = qs.filter(classify.node_filter(kind, obj))
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(body__icontains=q))
    if today:
        qs = qs.filter(created_at__date=timezone.localdate())  # 오늘 만든 글 (원고에서 온 글은 원고를 쓴 날)
    if custom:
        qs = qs.filter(custom=True)
    return qs


def _in_stage(qs, key):
    """탭의 글: 발행예정글은 아직 발행 안 한 것, 게시글 관리는 발행 완료한 것."""
    if key == "done":
        return qs.filter(stage="post", publish_status=qs.model.Publish.DONE)
    if key == "post":
        return qs.filter(stage="post").exclude(publish_status=qs.model.Publish.DONE)
    return qs.filter(stage=key)


def tab_of(post):
    """글이 보이는 탭"""
    return "done" if post.stage == "post" and post.publish_status == post.Publish.DONE else post.stage


def _params(request, stage=None):
    """목록 조건: 단계 · 분류(sel) · 검색어 · 오늘 · 커스텀. 모르는 값은 버린다.
    발행예정글·게시글 관리는 분류로 나누지 않는다 (2026-10-21 사용자: 트리·분류 줄 없이 날짜순)."""
    get = request.GET
    stage = get.get("stage") if get.get("stage") in STAGE_KEYS else (stage or "temp")
    sel = get.get("sel", "") if stage not in TABLE_STAGES else ""
    kind, obj = _find(sel)
    if kind not in CLASS_KINDS or obj is None:
        sel, kind, obj = "", None, None
    view = "list" if stage not in TABLE_STAGES and get.get("view") == "list" else ""  # 임시글·검토글 목록 보기
    site = get.get("site", "") if get.get("site", "") in sites.names() else ""
    return {"stage": stage, "sel": sel, "kind": kind, "obj": obj, "view": view, "site": site,
            "q": get.get("q", "").strip(), "today": get.get("today") == "1", "custom": get.get("custom") == "1"}


def _query(p, **override):
    """조건을 주소 뒤에 붙일 문자열로 (빈 값은 뺀다)."""
    vals = {"stage": p["stage"], "sel": p["sel"], "q": p["q"], "today": "1" if p["today"] else "",
            "custom": "1" if p.get("custom") else "", "site": p.get("site", ""), "view": p.get("view", "")}
    vals.update(override)
    return urlencode({k: v for k, v in vals.items() if v})


def _collect(p, prefetch=False):
    """두 편집기의 글을 한 목록으로 (만든 순서, 최신이 위) + 단계별 글 수."""
    posts, counts = [], dict.fromkeys(STAGE_KEYS, 0)
    for w in classify.WRITERS:
        base = _filtered(w, p["kind"], p["obj"], p["q"], p["today"], p["custom"], p.get("site", ""))
        for key in STAGE_KEYS:
            counts[key] += _in_stage(base, key).count()
        qs = classify.with_classification(_in_stage(base, p["stage"]))
        if prefetch or p["stage"] == "done":  # 게시글 관리는 넣은 곳(카테고리) 순으로 늘어놓는다
            qs = qs.prefetch_related(Prefetch("placements", queryset=_placements_qs()))
        for post in qs:
            post.writer = w
            post.ref = f"{w}:{post.pk}"
            post.writer_label = "네이버" if w == "naver" else "티스토리"  # 편집기 (분류가 아니다)
            posts.append(post)
    posts.sort(key=lambda x: (x.created_at, x.pk), reverse=True)  # 만든 순서로 고정 (상태를 바꿔도 자리가 그대로)
    if p["stage"] == "post":  # 발행예정글: 발행 예정일 빠른 순 → 사이트(운영 화면 순서) → 최신 순. 날짜 없는 글은 끝
        order = {name: i for i, name in enumerate(sites.names())}
        posts.sort(key=lambda x: (x.planned_on.toordinal() if x.planned_on else float("inf"), order.get(x.target, len(order))))
    elif p["stage"] == "done":  # 게시글 관리 (2026-10-23 사용자): 사이트 → 카테고리 → 발행일(최근이 위)
        order = {name: i for i, name in enumerate(sites.names())}
        posts.sort(key=lambda x: -(x.published_on or x.created_at.date()).toordinal())
        posts.sort(key=lambda x: (order.get(site_of(x), len(order)), _category_key(x)))
    elif p["stage"] == "temp":  # 임시글: 사이트별로 묶어(운영 화면 순서, 사이트 없는 글은 끝), 그 안에서 최신 순 (2026-10-22 사용자)
        order = {name: i for i, name in enumerate(sites.names())}
        posts.sort(key=lambda x: order.get(x.target, len(order)))
    return posts, counts


def site_of(post):
    """글의 사이트: 고른 사이트, 없으면 넣은 곳의 사이트 (placements 를 미리 읽어 둔 글)."""
    if post.target:
        return post.target
    pls = list(post.placements.all())
    return pls[0].site_category.blog.name if pls else ""


def _category_key(post):
    """넣은 곳(첫 번째)의 사이트 카테고리 순서: 상위 카테고리 순서 → 그 아래 하위 순서. 넣은 곳 없는 글은 끝."""
    pls = list(post.placements.all())
    if not pls:
        return (1,)
    c = pls[0].site_category
    top = c.parent or c
    return (0, top.order, top.pk, (c.order, c.pk) if c.parent_id else (-1, 0))


def index(request):
    """예전 '글 관리' 주소 (2026-10-22 사용자: 메뉴에서 뺐다) → 지금의 글 관리(posts:view)로, 조건 그대로."""
    q = request.GET.urlencode()
    return redirect(f"{reverse('posts:view')}{'?' + q if q else ''}")


def _import_new_drafts(request):
    from apps.writing.views import auto_import_drafts
    added = auto_import_drafts()  # 루틴이 새로 쓴 원고를 임시글으로
    if added:
        messages.success(request, f"새 원고 {added}편을 임시글으로 가져왔습니다.")


def _mode_urls(p):
    """임시글·검토글의 보기 바꾸기: 한 건씩 · 목록 (조건은 그대로)."""
    if p["stage"] in TABLE_STAGES:
        return None
    return {"one": f"{reverse('posts:view')}?{_query(p, view='')}", "list": f"{reverse('posts:view')}?{_query(p, view='list')}",
            "on": p["view"] or "one"}


DAY_NAMES = "월화수목금토일"
# 표의 발행 버튼은 짧게 (2026-10-23 사용자: 발행예정글 표의 버튼 글씨를 줄인다)
PUBLISH_SHORT = [("todo", "미발행"), ("done", "발행")]


def _day_heads(posts):
    """발행 예정일 정한 글(날짜순)에 날짜 묶음 머리: 묶음 첫 글에 (날짜, 요일, 글 수, 오늘인가, 지났나)."""
    by_day, today, seen = Counter(x.planned_on for x in posts), timezone.localdate(), set()
    for x in posts:
        if x.planned_on and x.planned_on not in seen:
            seen.add(x.planned_on)
            x.day_head = {"day": x.planned_on, "dow": DAY_NAMES[x.planned_on.weekday()], "count": by_day[x.planned_on],
                          "today": x.planned_on == today, "past": x.planned_on < today}


def _list_page(request, p, template="blog_types/posts.html", base="posts:view", extra=None):
    """글 관리 목록 (분류 트리 없이 표만): 발행예정글, 또는 목록 보기로 바꾼 임시글·검토글.
    중메뉴 발행예정글(planned)도 같은 내용을 다른 화면(template)으로 쓴다. base: 조건 지우기가 갈 주소."""
    sel, kind, obj, q, today, stage = p["sel"], p["kind"], p["obj"], p["q"], p["today"], p["stage"]
    if stage == "post":  # 전에 담아 카테고리가 빈 발행예정글도 원고의 '넣을 카테고리'로 (한 번도 넣은 적 없는 글만)
        for writer in ("tistory", "naver"):
            sites.place_defaults(classify.post_model(writer).objects.filter(stage="post"))
    posts, counts = _collect(p, prefetch=stage in TABLE_STAGES)
    list_q = _query(p, view="")  # 제목을 누르면 한 건씩 보기로 (같은 조건의 목록과 함께)
    groups = _site_groups() if stage in TABLE_STAGES else []  # 카테고리 칸에서 바로 넣는다
    for post in posts:
        post.list_url = _view_url(post, list_q)
        post.path_label = classify.label_of(post)
        post.site_groups = sorted(groups, key=lambda g, t=post.target: g[0] != t)  # 그 글의 사이트를 맨 위에
    # 변환 가능 글 전체 변환 (2026-10-22 사용자): 보이는 글 중 넣은 곳이 미변환인 것
    ready = [str(pl.pk) for post in posts for pl in post.placements.all() if pl.convert_status == "none"]
    planned = [x for x in posts if x.planned_on]
    _day_heads(planned)
    return render(request, template, {
        "page_title": "글 관리",
        "sel": sel, "q": q, "stage": p["stage"], "today": today,
        "today_url": "?" + _query(p, today="" if today else "1"),
        "custom": p["custom"], "custom_url": "?" + _query(p, custom="" if p["custom"] else "1"),
        "tabs": [{"key": k, "label": label, "count": counts[k], "on": k == stage,
                  "url": f"{reverse('posts:view')}?{_query(p, stage=k, view=p['view'] if k not in TABLE_STAGES else '')}"}
                 for k, label in STAGES if k in TAB_KEYS],
        "list_mode": p["view"] == "list", "mode_urls": _mode_urls(p), "table_stage": stage in TABLE_STAGES,
        "plan_split": stage == "post",  # 예정일 없는 글 · 정한 글을 두 표로 (2026-10-22 사용자)
        "unplanned": [x for x in posts if not x.planned_on], "planned": planned,
        "clear_url": f"{reverse(base)}?{_query(p, sel='', q='', today='', custom='', site='')}",
        "site_filter": p["site"],
        "path": [label for label, _ in _path(kind, obj)][1:] if kind else [],  # 맨 앞 '모든 글'은 빼고
        "posts": posts,
        "ready_ids": ",".join(ready), "ready_count": len(ready),
        "site_names": sites.names(),
        "publish_choices": PUBLISH_SHORT,
        **(extra or {}),
    })


def planned(request):
    """블로그·카페 › 발행예정글 (2026-10-23 사용자): 날짜를 정해 두고 그날 각 블로그에 쓰는 화면이라 매일 많이 쓴다.
    글 관리의 발행예정글 탭과 같은 기능(사이트 · 카테고리 · 변환 · 발행 · 예정일 · 갱신)을, 두 표(예정일 없음 · 정함)를 크게."""
    request.nav_key = "posts_planned"
    p = _params(request, stage="post")
    p.update(stage="post", sel="", kind=None, obj=None, view="")
    return _list_page(request, p, template="blog_types/posts_planned.html", base="posts:planned",
                      extra={"page_title": "발행예정글"})


def published(request):
    """블로그·카페 › 게시글 관리 (2026-10-23 사용자: 글 관리 탭에서 중메뉴로): 발행 완료한 글.
    사이트 → 카테고리 → 발행일 순. 조건은 검색 · 오늘(오늘 발행한 글) · 사이트 · 전체만."""
    request.nav_key = "posts_published"
    get = request.GET
    q, today = get.get("q", "").strip(), get.get("today") == "1"
    p = {"stage": "done", "sel": "", "kind": None, "obj": None, "view": "", "site": "", "q": q, "today": False, "custom": False}
    posts, _ = _collect(p, prefetch=True)
    if today:
        posts = [x for x in posts if x.published_on == timezone.localdate()]
    names, by_site = sites.names(), Counter(site_of(x) for x in posts)
    site = get.get("site", "") if get.get("site", "") in names else ""
    if site:
        posts = [x for x in posts if site_of(x) == site]
    base = reverse("posts:published")

    def url(**override):
        vals = {"q": q, "today": "1" if today else "", "site": site, **override}
        query = urlencode({k: v for k, v in vals.items() if v})
        return f"{base}?{query}" if query else base

    groups = []  # 사이트 › 카테고리 묶음마다 머리 한 줄 (이름 · 글 수)
    for x in posts:
        pls = list(x.placements.all())
        x.site_name = site_of(x)
        label = f"{x.site_name or '사이트 없음'} › {pls[0].site_category if pls else '카테고리 없음'}"
        if not groups or groups[-1][0] != label:
            groups.append([label, x, 0])
        groups[-1][2] += 1
    for label, first, count in groups:
        first.group_head = (label, count)
    return render(request, "blog_types/posts_published.html", {
        "page_title": "게시글 관리",
        "posts": posts, "q": q, "today": today, "site_filter": site,
        "today_url": url(today="" if today else "1"),
        "site_buttons": [{"name": n, "count": by_site[n], "on": n == site, "url": url(site="" if n == site else n)} for n in names],
        "all_url": base, "filtered": bool(q or today or site),
        "publish_choices": PUBLISH_SHORT,
    })


def _view_url(post, list_q=""):
    """글 보기 주소: 목록 조건 + 고른 글 (p=tistory:3)."""
    pick = f"p={classify.writer_of(post)}:{post.pk}"
    return f"{reverse('posts:view')}?{list_q + '&' if list_q else ''}{pick}"


def _one(value):
    writer, _, pk = (value or "").partition(":")
    if writer in classify.WRITERS and pk.isdigit():
        return classify.post_model(writer).objects.filter(pk=pk).first()
    return None


def post_list_for(request, post):
    """글 보기 왼쪽의 글 목록: 단계 탭(임시글·검토글·발행예정글)의 글 + 글 관리에서 넘어온 조건(분류·검색·오늘).
    단계가 주소에 없으면 그 글의 단계. 위·아래 화살표, 옮기기·휴지통 뒤에 갈 글도 이 목록 순서를 따른다 (한 건씩 처리)."""
    p = _params(request, stage=tab_of(post))
    p["view"] = ""  # 한 건씩 보기
    posts, counts = _collect(p)
    # 검토글·발행예정글: 넣은 곳 · 변환 (2026-10-22 사용자: 검토글에서도 카테고리 고르고 변환해 보고 발행예정으로)
    placements = (list(post.placements.select_related("site_category__blog", "site_category__parent"))
                  if post.stage in ("review", "post") else [])
    list_q = _query(p)
    me = (classify.writer_of(post), post.pk)
    current = None
    for item in posts:
        item.list_url = _view_url(item, list_q)
        item.path_label = classify.label_of(item)
        if (item.writer, item.pk) == me:
            current = item
    if p["stage"] == "temp":  # 임시글: 사이트 묶음마다 첫 글에 머리 (이름 · 글 수) — 2026-10-22 사용자: 잘 안 보인다
        by_site, seen = Counter(item.target for item in posts), set()
        for item in posts:
            if item.target not in seen:
                seen.add(item.target)
                item.group_head = (item.target or "사이트 없음", by_site[item.target])
    keep = _query(p, stage="")
    ctx = {
        "pl_items": posts,
        "pl_current": current,
        "pl_stage": p["stage"], "pl_stage_label": dict(STAGES)[p["stage"]],
        "pl_q": p["q"], "pl_sel": p["sel"], "pl_today": p["today"], "pl_custom": p["custom"],
        "pl_path": [label for label, _ in _path(p["kind"], p["obj"])][1:] if p["kind"] else [],
        "pl_today_url": f"{reverse('posts:view')}?{_query(p, today='' if p['today'] else '1')}",
        "pl_custom_url": f"{reverse('posts:view')}?{_query(p, custom='' if p['custom'] else '1')}",
        "pl_clear_url": f"{reverse('posts:view')}?{_query(p, sel='', q='', today='', custom='')}",
        "pl_query": list_q,
        "pl_keep": keep,
        "pl_tabs": [{"key": k, "label": label, "count": counts[k], "on": k == p["stage"],
                     "url": f"{reverse('posts:view')}?{_query(p, stage=k)}"} for k, label in STAGES if k in TAB_KEYS],
        "pl_next_url": f"{reverse('posts:view')}?{list_q}",  # 옮기기·휴지통 뒤: 목록의 다음 글 (없으면 이 단계 첫 글)
        "site_names": sites.names(),
        "post_placements": placements,
        "post_site_groups": sorted(_site_groups(), key=lambda g: g[0] != post.target) if post.stage in ("review", "post") else [],
        "post_ref": f"{classify.writer_of(post)}:{post.pk}",
        "mode_urls": _mode_urls(p),
    }
    if current is not None:  # 목록에 없으면(조건에 안 맞는 글) 화살표는 원래대로 그 편집기의 같은 단계 순서
        i = posts.index(current)
        ctx["above"] = posts[i - 1] if i > 0 else None
        ctx["below"] = posts[i + 1] if i + 1 < len(posts) else None
        nxt = ctx["below"] or ctx["above"]
        if nxt is not None:
            ctx["pl_next_url"] = nxt.list_url
    return ctx


def view(request):
    """블로그·카페 › 글 보기: 한 건씩 보면서 처리한다. ?stage=…&p=tistory:3 (+ 분류·검색·오늘).
    고른 글이 없으면 그 단계 목록의 첫 글. 단계에 글이 없으면 빈 화면. 발행예정글은 고른 글이 없으면 글 관리와 같은 전체 목록."""
    request.nav_key = "posts_view"
    _import_new_drafts(request)
    post = _one(request.GET.get("p"))
    if post is None and request.GET.get("stage") == "done":  # 게시글 관리는 중메뉴로 옮겼다 (2026-10-23 사용자)
        keep = urlencode({k: request.GET[k] for k in ("q", "site") if request.GET.get(k)})
        return redirect(f"{reverse('posts:published')}{'?' + keep if keep else ''}")
    if post is None and (request.GET.get("stage") in TABLE_STAGES or _params(request)["view"] == "list"):
        return _list_page(request, _params(request))  # 목록 보기 · 발행예정글은 한 건 대신 전체 목록 (2026-10-20 사용자)
    if post is None:
        posts, _ = _collect(_params(request))
        post = posts[0] if posts else None
    if post is not None:
        if classify.writer_of(post) == "naver":
            from apps.naver_writing.views import render_detail
        else:
            from apps.writing.views import render_detail
        return render_detail(request, post)
    p = _params(request)
    _, counts = _collect(p)
    return render(request, "blog_types/view_empty.html", {
        "page_title": "글 관리",
        "pl_stage_label": dict(STAGES)[p["stage"]],
        "pl_tabs": [{"key": k, "label": label, "count": counts[k], "on": k == p["stage"],
                     "url": f"{reverse('posts:view')}?{_query(p, stage=k)}"} for k, label in STAGES if k in TAB_KEYS],
        "pl_clear_url": f"{reverse('posts:view')}?{_query(p, sel='', q='', today='', custom='')}",
        "has_filter": bool(p["sel"] or p["q"] or p["today"] or p["custom"]),
    })


def _picked(request):
    """체크한 글: 'tistory:3' · 'naver:5'"""
    out = []
    for value in request.POST.getlist("ids"):
        writer, _, pk = value.partition(":")
        if writer in classify.WRITERS and pk.isdigit():
            post = classify.post_model(writer).objects.filter(pk=pk).first()
            if post:
                out.append(post)
    return out


def _back(request):
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else reverse("posts:view"))


@require_POST
def site(request):
    """글의 사이트 고르기 (글 관리·글 보기의 검토글·발행예정글). ids 는 'tistory:3' 꼴, 여러 개면 한꺼번에. 빈 값은 사이트 지우기."""
    posts = _picked(request)
    value = request.POST.get("site", "").strip()
    if value and value not in sites.names():
        messages.warning(request, "없는 사이트입니다.")
        return _back(request)
    for post in posts:
        if post.target != value:
            post.target = value
            post.save(update_fields=["target", "updated_at"])
    if not posts:
        messages.warning(request, "먼저 글을 고르세요.")
    elif len(posts) > 1:
        messages.success(request, f"{len(posts)}건의 사이트를 {value or '없음'}(으)로 정했습니다.")
    return _back(request)


@require_POST
def plan(request):
    """발행 예정일 정하기 (발행예정글 줄마다). post='tistory:3', day=YYYY-MM-DD (빈 값이면 지운다)."""
    post = _one(request.POST.get("post"))
    if post is None:
        messages.warning(request, "글을 찾을 수 없습니다.")
        return _back(request)
    raw = request.POST.get("day", "").strip()
    try:
        post.planned_on = timezone.datetime.fromisoformat(raw).date() if raw else None
    except ValueError:
        messages.warning(request, "날짜를 YYYY-MM-DD 로 넣으세요.")
        return _back(request)
    post.save(update_fields=["planned_on", "updated_at"])
    return _back(request)


@require_POST
def promote(request):
    """임시글·검토글을 한 번에 발행예정글로 (모니터링 › 오늘의 글, 2026-10-23 사용자: 바로 발행예정글로 갈 수 있게).
    예정일이 없으면 오늘로 — 옮긴 글이 모니터링 '오늘 발행'에 바로 보인다."""
    posts = [p for p in _picked(request) if p.stage in ("temp", "review")]
    for post in posts:
        post.stage = "post"
        post.planned_on = post.planned_on or timezone.localdate()
        post.save(update_fields=["stage", "planned_on", "updated_at"])
    if posts:
        messages.success(request, f"{len(posts)}건을 발행예정글로 옮겼습니다.")
    return _back(request)


@require_POST
def bulk(request):
    """체크한 글을 이웃 단계로 옮기거나(to), 상대 글쓰기로 보내거나(send), 발행 상태를 바꾼다(publish=done|todo).
    두 글쓰기 글이 섞여 있어도 된다."""
    posts = _picked(request)
    back = _back(request)
    if not posts:
        messages.warning(request, "먼저 글을 체크하세요.")
        return back
    if request.POST.get("plan"):  # 발행 예정일 한꺼번에 (2026-10-22 사용자). 날짜를 비우면 지운다
        raw = request.POST.get("plan_day", "").strip()
        try:
            day = timezone.datetime.fromisoformat(raw).date() if raw else None
        except ValueError:
            messages.warning(request, "날짜를 YYYY-MM-DD 로 넣으세요.")
            return back
        for post in posts:
            post.planned_on = day
            post.save(update_fields=["planned_on", "updated_at"])
        messages.success(request, f"{len(posts)}건의 발행 예정일을 {day:%Y-%m-%d}(으)로 정했습니다." if day else f"{len(posts)}건의 발행 예정일을 지웠습니다.")
        return back
    publish = request.POST.get("publish")
    if publish in ("done", "todo"):
        targets = [post for post in posts if post.stage == "post"]
        for post in targets:
            sites.publish(post, publish == "done")
        label = "발행 완료" if publish == "done" else "미발행"
        if targets:
            messages.success(request, f"{len(targets)}건을 {label}(으)로 바꿨습니다. 넣은 곳(사이트 카테고리)의 상태도 같이 바꿨습니다.")
        if len(targets) < len(posts):
            messages.warning(request, f"{len(posts) - len(targets)}건은 발행예정글이 아니라 그대로 두었습니다.")
        return back
    if request.POST.get("send"):
        for post in posts:
            transfer.send(post)
        messages.success(request, f"{len(posts)}건을 상대 글쓰기 임시글으로 보냈습니다. (원래 글은 그대로)")
        return back
    to = request.POST.get("to", "")
    moved = []
    for post in posts:
        if post.can_move_to(to):
            post.stage = to
            post.save(update_fields=["stage", "updated_at"])
            moved.append(post)
    if to == "post":  # 발행예정글: 카테고리가 비면 원고의 '넣을 카테고리'로 (2026-10-23 사용자)
        sites.place_defaults(moved)
    moved = len(moved)
    if moved:
        messages.success(request, f"{moved}건을 {dict(STAGES)[to]}(으)로 옮겼습니다.")
    if moved < len(posts):
        messages.warning(request, f"{len(posts) - moved}건은 옮길 수 없습니다. (발행 완료한 글은 되돌리지 않습니다)")
    return back

