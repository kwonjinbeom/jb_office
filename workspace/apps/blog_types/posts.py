"""글 관리: 모든 글을 한 화면에서 (2026-10-16 사용자). 편집기(티스토리·네이버) 구분은 쓰지 않는다 —
사이트·플랫폼에 맞추는 건 사이트별 템플릿의 변환에서 한다. 새 글은 한 표(writing.Post)에 만든다.

왼쪽은 카테고리 관리와 같은 글 분류 트리(모든 글 › 대분류 · 미분류 › 카테고리 › 타입 › 하위, 티스토리·네이버 나눔 없음), 오른쪽은 임시글 → 검토글 →
발행예정글 탭과 그 단계의 글. 트리에서 고르면 그 아래 글만 보인다. 글 보기·쓰기·상태 바꾸기·옮기기는 각 글쓰기 앱의 주소를 그대로 쓴다
(글은 여전히 writing.Post / naver_writing.Post 두 표에 있다).

주소: ?stage=temp|review|post &sel=g1|c3|t5|s9|u &q=검색어 &today=1(오늘 만든 글만) &view=list(임시글·검토글을 목록으로)

보기 (2026-10-22 사용자): 임시글·검토글은 기본이 한 건씩 보기(글 화면 + 왼쪽 글 목록), '목록'으로 바꾸면 체크해서 한꺼번에
옮기기·삭제하는 표. 발행예정글은 늘 표.

글을 누르면 글 보기(각 글쓰기 앱의 detail)로 간다. 글 보기 왼쪽에는 분류 트리 대신 같은 조건(단계·분류·검색·오늘)의
글 목록을 보여 준다 (post_list_for). 조건은 주소에 그대로 실어 보낸다 (2026-10-17 사용자).

단계별 칸 (2026-10-17 사용자): 임시글은 사이트(읽기)·내용, 검토글은 사이트 고르기, 발행예정글은 사이트 고르기 ·
넣은 곳(사이트 › 카테고리) · 변환 · 발행(미발행/발행 완료, 한 건씩 또는 체크한 것 한꺼번에). 작성 상태는 글 보기에서.
"""
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Prefetch, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import classify, sites, transfer
from .views import _find, _path, _placements_qs, _site_groups

STAGES = [("temp", "임시글"), ("review", "검토글"), ("post", "발행예정글")]
STAGE_KEYS = [k for k, _ in STAGES]
CLASS_KINDS = {"section", "category", "type", "sub", "unclassified"}


def _filtered(writer, kind, obj, q, today=False):
    qs = classify.post_model(writer).objects.all()
    if kind in CLASS_KINDS:
        qs = qs.filter(classify.node_filter(kind, obj))
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(body__icontains=q))
    if today:
        qs = qs.filter(created_at__date=timezone.localdate())  # 오늘 만든 글 (원고에서 온 글은 원고를 쓴 날)
    return qs


PUBLISH_FILTERS = [("", "전체"), ("todo", "미발행"), ("done", "발행 완료")]


def _params(request, stage=None):
    """목록 조건: 단계 · 분류(sel) · 검색어 · 오늘 · 발행(pub, 발행예정글만). 모르는 값은 버린다.
    발행예정글은 분류로 나누지 않는다 (2026-10-21 사용자: 트리·분류 줄 없이 미발행 → 날짜순)."""
    get = request.GET
    stage = get.get("stage") if get.get("stage") in STAGE_KEYS else (stage or "temp")
    sel = get.get("sel", "") if stage != "post" else ""
    kind, obj = _find(sel)
    if kind not in CLASS_KINDS or obj is None:
        sel, kind, obj = "", None, None
    pub = get.get("pub", "") if stage == "post" and get.get("pub") in ("todo", "done") else ""
    view = "list" if stage != "post" and get.get("view") == "list" else ""  # 임시글·검토글 목록 보기
    return {"stage": stage, "sel": sel, "kind": kind, "obj": obj, "pub": pub, "view": view,
            "q": get.get("q", "").strip(), "today": get.get("today") == "1"}


def _query(p, **override):
    """조건을 주소 뒤에 붙일 문자열로 (빈 값은 뺀다)."""
    vals = {"stage": p["stage"], "sel": p["sel"], "q": p["q"], "today": "1" if p["today"] else "", "pub": p.get("pub", ""),
            "view": p.get("view", "")}
    vals.update(override)
    return urlencode({k: v for k, v in vals.items() if v})


def _collect(p, prefetch=False):
    """두 편집기의 글을 한 목록으로 (만든 순서, 최신이 위) + 단계별 글 수."""
    posts, counts = [], dict.fromkeys(STAGE_KEYS, 0)
    for w in classify.WRITERS:
        base = _filtered(w, p["kind"], p["obj"], p["q"], p["today"])
        for key in STAGE_KEYS:
            counts[key] += base.filter(stage=key).count()
        qs = classify.with_classification(base.filter(stage=p["stage"]))
        if p.get("pub"):
            qs = qs.filter(publish_status=p["pub"])
        if prefetch:
            qs = qs.prefetch_related(Prefetch("placements", queryset=_placements_qs()))
        for post in qs:
            post.writer = w
            post.ref = f"{w}:{post.pk}"
            post.writer_label = "네이버" if w == "naver" else "티스토리"  # 편집기 (분류가 아니다)
            posts.append(post)
    posts.sort(key=lambda x: (x.created_at, x.pk), reverse=True)  # 만든 순서로 고정 (상태를 바꿔도 자리가 그대로)
    if p["stage"] == "post":  # 발행예정글: 미발행이 위, 그 안에서 최신 순
        posts.sort(key=lambda x: x.publish_status == x.Publish.DONE)
    return posts, counts


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
    if p["stage"] == "post":
        return None
    return {"one": f"{reverse('posts:view')}?{_query(p, view='')}", "list": f"{reverse('posts:view')}?{_query(p, view='list')}",
            "on": p["view"] or "one"}


def _list_page(request, p):
    """글 관리 목록 (분류 트리 없이 표만): 발행예정글, 또는 목록 보기로 바꾼 임시글·검토글."""
    sel, kind, obj, q, today, stage = p["sel"], p["kind"], p["obj"], p["q"], p["today"], p["stage"]
    posts, counts = _collect(p, prefetch=stage == "post")
    list_q = _query(p, view="")  # 제목을 누르면 한 건씩 보기로 (같은 조건의 목록과 함께)
    groups = _site_groups() if stage == "post" else []  # 카테고리 칸에서 바로 넣는다
    for post in posts:
        post.list_url = _view_url(post, list_q)
        post.path_label = classify.label_of(post)
        post.site_groups = sorted(groups, key=lambda g, t=post.target: g[0] != t)  # 그 글의 사이트를 맨 위에
    # 변환 가능 글 전체 변환 (2026-10-22 사용자): 보이는 글 중 넣은 곳이 미변환인 것
    ready = [str(pl.pk) for post in posts for pl in post.placements.all() if pl.convert_status == "none"]
    return render(request, "blog_types/posts.html", {
        "page_title": "글 관리",
        "sel": sel, "q": q, "stage": p["stage"], "today": today,
        "today_url": "?" + _query(p, today="" if today else "1"),
        "tabs": [{"key": k, "label": label, "count": counts[k], "on": k == stage,
                  "url": f"{reverse('posts:view')}?{_query(p, stage=k, pub='', view=p['view'] if k != 'post' else '')}"}
                 for k, label in STAGES],
        "list_mode": p["view"] == "list", "mode_urls": _mode_urls(p),
        "clear_url": f"{reverse('posts:view')}?{_query(p, sel='', q='', today='', pub='')}",
        "path": [label for label, _ in _path(kind, obj)][1:] if kind else [],  # 맨 앞 '모든 글'은 빼고
        "posts": posts,
        "pub": p["pub"],
        "ready_ids": ",".join(ready), "ready_count": len(ready),
        "pub_filters": [{"key": k, "label": label, "on": k == p["pub"], "url": "?" + _query(p, pub=k)} for k, label in PUBLISH_FILTERS],
        "site_names": sites.names(),
        "publish_choices": classify.post_model("tistory").Publish.choices,
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
    p = _params(request, stage=post.stage)
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
    keep = _query(p, stage="")
    ctx = {
        "pl_items": posts,
        "pl_current": current,
        "pl_stage": p["stage"], "pl_stage_label": dict(STAGES)[p["stage"]],
        "pl_q": p["q"], "pl_sel": p["sel"], "pl_today": p["today"],
        "pl_path": [label for label, _ in _path(p["kind"], p["obj"])][1:] if p["kind"] else [],
        "pl_today_url": f"{reverse('posts:view')}?{_query(p, today='' if p['today'] else '1')}",
        "pl_clear_url": f"{reverse('posts:view')}?{_query(p, sel='', q='', today='')}",
        "pl_query": list_q,
        "pl_keep": keep,
        "pl_tabs": [{"key": k, "label": label, "count": counts[k], "on": k == p["stage"],
                     "url": f"{reverse('posts:view')}?{_query(p, stage=k)}"} for k, label in STAGES],
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
    if post is None and (request.GET.get("stage") == "post" or _params(request)["view"] == "list"):
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
                     "url": f"{reverse('posts:view')}?{_query(p, stage=k)}"} for k, label in STAGES],
        "pl_clear_url": f"{reverse('posts:view')}?{_query(p, sel='', q='', today='')}",
        "has_filter": bool(p["sel"] or p["q"] or p["today"]),
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
def bulk(request):
    """체크한 글을 이웃 단계로 옮기거나(to), 상대 글쓰기로 보내거나(send), 발행 상태를 바꾼다(publish=done|todo).
    두 글쓰기 글이 섞여 있어도 된다."""
    posts = _picked(request)
    back = _back(request)
    if not posts:
        messages.warning(request, "먼저 글을 체크하세요.")
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
    moved = 0
    for post in posts:
        if post.can_move_to(to):
            post.stage = to
            post.save(update_fields=["stage", "updated_at"])
            moved += 1
    if moved:
        messages.success(request, f"{moved}건을 {dict(STAGES)[to]}(으)로 옮겼습니다.")
    if moved < len(posts):
        messages.warning(request, f"{len(posts) - moved}건은 옮길 수 없습니다. (발행 완료한 글은 되돌리지 않습니다)")
    return back

