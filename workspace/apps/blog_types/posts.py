"""글 관리: 모든 글을 한 화면에서 (2026-10-16 사용자). 편집기(티스토리·네이버) 구분은 쓰지 않는다 —
사이트·플랫폼에 맞추는 건 사이트별 템플릿의 변환에서 한다. 새 글은 한 표(writing.Post)에 만든다.

왼쪽은 글 매핑 관리와 같은 글 분류 트리(모든 글 › 대분류 · 미분류 › 카테고리 › 타입 › 하위, 티스토리·네이버 나눔 없음), 오른쪽은 임시글 → 검토글 →
발행예정글 탭과 그 단계의 글. 트리에서 고르면 그 아래 글만 보인다. 글 보기·쓰기·상태 바꾸기·옮기기는 각 글쓰기 앱의 주소를 그대로 쓴다
(글은 여전히 writing.Post / naver_writing.Post 두 표에 있다).

주소: ?stage=temp|review|post &sel=g1|c3|t5|s9|u &q=검색어 &today=1(오늘 만든 글만)

글을 누르면 글 보기(각 글쓰기 앱의 detail)로 간다. 글 보기 왼쪽에는 분류 트리 대신 같은 조건(단계·분류·검색·오늘)의
글 목록을 보여 준다 (post_list_for). 조건은 주소에 그대로 실어 보낸다 (2026-10-17 사용자).
"""
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Prefetch, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import classify, transfer
from .views import _find, _open_branches, _path, _placements_qs

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


def _params(request, stage=None):
    """목록 조건: 단계 · 분류(sel) · 검색어 · 오늘. 모르는 값은 버린다."""
    get = request.GET
    stage = get.get("stage") if get.get("stage") in STAGE_KEYS else (stage or "temp")
    sel = get.get("sel", "")
    kind, obj = _find(sel)
    if kind not in CLASS_KINDS or obj is None:
        sel, kind, obj = "", None, None
    return {"stage": stage, "sel": sel, "kind": kind, "obj": obj,
            "q": get.get("q", "").strip(), "today": get.get("today") == "1"}


def _query(p, **override):
    """조건을 주소 뒤에 붙일 문자열로 (빈 값은 뺀다)."""
    vals = {"stage": p["stage"], "sel": p["sel"], "q": p["q"], "today": "1" if p["today"] else ""}
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
        if prefetch:
            qs = qs.prefetch_related(Prefetch("placements", queryset=_placements_qs()))
        for post in qs:
            post.writer = w
            post.writer_label = "네이버" if w == "naver" else "티스토리"  # 편집기 (분류가 아니다)
            posts.append(post)
    posts.sort(key=lambda x: (x.created_at, x.pk), reverse=True)  # 만든 순서로 고정 (상태를 바꿔도 자리가 그대로)
    return posts, counts


def index(request):
    request.nav_key = "posts"
    from apps.writing.views import auto_import_drafts
    added = auto_import_drafts()  # 루틴이 새로 쓴 원고를 임시글으로
    if added:
        messages.success(request, f"새 원고 {added}편을 임시글으로 가져왔습니다.")
    p = _params(request)
    stage, sel, kind, obj, q, today = p["stage"], p["sel"], p["kind"], p["obj"], p["q"], p["today"]
    posts, counts = _collect(p, prefetch=stage == "post")
    list_q = _query(p)
    for post in posts:
        post.list_url = _view_url(post, list_q)  # 글 보기 (같은 조건의 목록과 함께)

    path = [label for label, _ in _path(kind, obj)][1:] if kind else []  # 맨 앞 '모든 글'은 빼고
    keep = f"stage={stage}&" + ("today=1&" if today else "")
    return render(request, "blog_types/posts.html", {
        "page_title": "글 관리",
        "tree": classify.class_tree(),
        "sel": sel, "kind": kind,
        "open": _open_branches(kind, obj) if kind else set(),
        "q": q, "stage": stage, "keep": keep, "today": today,
        "filter_q": _query(p, stage=""),
        "today_url": "?" + _query(p, today="" if today else "1"),
        "tabs": [{"key": k, "label": label, "count": counts[k], "on": k == stage} for k, label in STAGES],
        "path": path,
        "posts": posts,
        "groups": classify.grouped(posts),
        "cols": 8 if stage == "post" else 6,  # 타겟 칸 포함
        "review_choices": classify.post_model("tistory").Review.choices,
        "write_choices": classify.post_model("tistory").Write.choices,
        "publish_choices": classify.post_model("tistory").Publish.choices,
        "next_to": {"temp": "review", "review": "post"}.get(stage),
        "prev_to": {"review": "temp", "post": "review"}.get(stage),
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
    posts, counts = _collect(p)
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
        "pl_index_url": f"{reverse('posts:index')}?{list_q}",
        "pl_next_url": f"{reverse('posts:view')}?{list_q}",  # 옮기기·휴지통 뒤: 목록의 다음 글 (없으면 이 단계 첫 글)
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
    고른 글이 없으면 그 단계 목록의 첫 글. 단계에 글이 없으면 빈 화면."""
    request.nav_key = "posts_view"
    post = _one(request.GET.get("p"))
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
        "page_title": "글 보기",
        "pl_stage_label": dict(STAGES)[p["stage"]],
        "pl_tabs": [{"key": k, "label": label, "count": counts[k], "on": k == p["stage"],
                     "url": f"{reverse('posts:view')}?{_query(p, stage=k)}"} for k, label in STAGES],
        "pl_index_url": f"{reverse('posts:index')}?{_query(p)}",
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


@require_POST
def bulk(request):
    """체크한 글을 이웃 단계로 옮기거나(to), 상대 글쓰기로 보낸다(send). 두 글쓰기 글이 섞여 있어도 된다."""
    posts = _picked(request)
    nxt = request.POST.get("next", "")
    back = redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else reverse("posts:index"))
    if not posts:
        messages.warning(request, "먼저 글을 체크하세요.")
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

