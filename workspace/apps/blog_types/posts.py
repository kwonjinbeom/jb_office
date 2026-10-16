"""글 관리: 티스토리 글쓰기 + 네이버 글쓰기를 한 화면에서 (2026-10-16 사용자).

왼쪽은 글 매핑 관리와 같은 글 분류 트리(모든 글 › 대분류 · 미분류 › 카테고리 › 타입 › 하위, 티스토리·네이버 나눔 없음), 오른쪽은 임시 템플릿 → 검토 템플릿 →
포스트 관리 탭과 그 단계의 글. 트리에서 고르면 그 아래 글만 보인다. 글 보기·쓰기·상태 바꾸기·옮기기는 각 글쓰기 앱의 주소를 그대로 쓴다
(글은 여전히 writing.Post / naver_writing.Post 두 표에 있다).

주소: ?stage=temp|review|post &sel=g1|c3|t5|s9|u &q=검색어
"""
from django.contrib import messages
from django.db.models import Prefetch, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import classify, transfer
from .views import _find, _open_branches, _path, _placements_qs

STAGES = [("temp", "임시 템플릿"), ("review", "검토 템플릿"), ("post", "포스트 관리")]
STAGE_KEYS = [k for k, _ in STAGES]
CLASS_KINDS = {"section", "category", "type", "sub", "unclassified"}


def _filtered(writer, kind, obj, q):
    qs = classify.post_model(writer).objects.all()
    if kind in CLASS_KINDS:
        qs = qs.filter(classify.node_filter(kind, obj))
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(body__icontains=q))
    return qs


def index(request):
    request.nav_key = "posts"
    stage = request.GET.get("stage") if request.GET.get("stage") in STAGE_KEYS else "temp"
    writers = list(classify.WRITERS)  # 두 편집기의 글을 함께
    sel = request.GET.get("sel", "")
    kind, obj = _find(sel)
    if kind not in CLASS_KINDS or obj is None:
        sel, kind, obj = "", None, None
    q = request.GET.get("q", "").strip()

    posts, counts = [], dict.fromkeys(STAGE_KEYS, 0)
    for w in writers:
        base = _filtered(w, kind, obj, q)
        for key in STAGE_KEYS:
            counts[key] += base.filter(stage=key).count()
        qs = classify.with_classification(base.filter(stage=stage))
        if stage == "post":
            qs = qs.prefetch_related(Prefetch("placements", queryset=_placements_qs()))
        for p in qs:
            p.writer = w
            p.writer_label = "네이버" if w == "naver" else "티스토리"  # 편집기 (분류가 아니다)
            posts.append(p)
    posts.sort(key=lambda p: (p.created_at, p.pk), reverse=True)  # 만든 순서로 고정 (상태를 바꿔도 자리가 그대로)

    path = [label for label, _ in _path(kind, obj)][1:] if kind else []  # 맨 앞 '모든 글'은 빼고
    keep = f"stage={stage}&"
    return render(request, "blog_types/posts.html", {
        "page_title": "글 관리",
        "tree": classify.class_tree(),
        "sel": sel, "kind": kind,
        "open": _open_branches(kind, obj) if kind else set(),
        "q": q, "stage": stage, "keep": keep,
        "filter_q": f"sel={sel}" if sel else "",
        "tabs": [{"key": k, "label": label, "count": counts[k], "on": k == stage} for k, label in STAGES],
        "path": path,
        "posts": posts,
        "groups": classify.grouped(posts),
        "cols": 8 if stage == "post" else 6,
        "review_choices": classify.post_model("tistory").Review.choices,
        "write_choices": classify.post_model("tistory").Write.choices,
        "publish_choices": classify.post_model("tistory").Publish.choices,
        "next_to": {"temp": "review", "review": "post"}.get(stage),
        "prev_to": {"review": "temp", "post": "review"}.get(stage),
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
        messages.success(request, f"{len(posts)}건을 상대 글쓰기 임시 템플릿으로 보냈습니다. (원래 글은 그대로)")
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
        messages.warning(request, f"{len(posts) - moved}건은 옮길 수 없습니다. (발행 완료한 포스트는 되돌리지 않습니다)")
    return back

