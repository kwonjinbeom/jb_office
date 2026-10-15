from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import drafts as drafts_mod
from .forms import PostForm
from .models import Post
from .render import clean_html, plain_text, render_body, text_to_html

Stage = Post.Stage

# 화면(stage) → 목록 주소 이름
LIST_URLS = {Stage.TEMP: "writing:list", Stage.REVIEW: "writing:review", Stage.POST: "writing:posts"}

# 목록에서 바로 바꾸는 상태 칸: 필드 이름 → 선택지
STATUS_FIELDS = {
    "review_status": Post.Review,
    "write_status": Post.Write,
    "publish_status": Post.Publish,
}


def _tabs(current):
    counts = dict(Post.objects.values_list("stage").annotate(n=Count("pk")))
    return [
        {"stage": s, "label": s.label, "url_name": LIST_URLS[s], "count": counts.get(s, 0), "on": s == current}
        for s in Stage
    ]


def _back(request, stage):
    """폼이 보낸 next(지금 보던 목록 주소)로, 없으면 그 화면 목록으로."""
    nxt = request.POST.get("next", "")
    if nxt.startswith("/") and not nxt.startswith("//"):
        return redirect(nxt)
    return redirect(LIST_URLS[stage])


def post_list(request, stage):
    q = request.GET.get("q", "").strip()
    # 만든 순서로 고정: 상태를 바꿔도 행이 자리를 옮기지 않게 한다.
    qs = Post.objects.filter(stage=stage).order_by("-created_at", "-pk")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(body__icontains=q))
    return render(
        request,
        "writing/list.html",
        {
            "page_title": Stage(stage).label,
            "stage": stage,
            "tabs": _tabs(stage),
            "posts": qs,
            "q": q,
            "next_label": {Stage.TEMP: "검토로", Stage.REVIEW: "포스트로"}.get(stage),
            "prev_label": {Stage.REVIEW: "임시로", Stage.POST: "검토로"}.get(stage),
            "review_choices": Post.Review.choices,
            "write_choices": Post.Write.choices,
            "publish_choices": Post.Publish.choices,
        },
    )


def import_drafts(request):
    """저장소 원고 폴더의 원고.md 를 골라 임시 템플릿으로 가져온다. 같은 제목이 이미 있으면 건너뛴다."""
    drafts = drafts_mod.list_drafts()
    existing = set(Post.objects.values_list("title", flat=True))
    if request.method == "POST":
        chosen = set(request.POST.getlist("keys"))
        added = 0
        for d in drafts:
            if d.key in chosen and d.title not in existing:
                Post.objects.create(stage=Stage.TEMP, title=d.title, body=d.body, tags=d.tags, summary=d.summary)
                existing.add(d.title)
                added += 1
        if added:
            messages.success(request, f"원고 {added}편을 임시 템플릿으로 가져왔습니다.")
        else:
            messages.warning(request, "가져올 원고를 고르세요. (이미 있는 원고는 건너뜁니다)")
        return redirect("writing:list")
    rows = [{"draft": d, "exists": d.title in existing,
             "chars": len("".join(plain_text(render_body(d.body), drop_slots=True).split()))} for d in drafts]
    return render(
        request,
        "writing/import.html",
        {"page_title": "원고 가져오기", "rows": rows, "folder": drafts_mod.drafts_dir(),
         "stage": Stage.TEMP, "tabs": _tabs(Stage.TEMP)},
    )


def create(request):
    stage = request.GET.get("stage") or request.POST.get("stage") or Stage.TEMP
    if stage not in Stage.values:
        stage = Stage.TEMP
    form = PostForm(request.POST or None, stage=stage)
    if request.method == "POST" and form.is_valid():
        post = form.save(commit=False)
        post.stage = stage
        post.save()
        messages.success(request, f"{Stage(stage).label}에 추가했습니다.")
        return redirect(post)
    return render(
        request,
        "writing/form.html",
        {"page_title": "새 포스트" if stage == Stage.POST else "새 템플릿", "form": form, "post": None,
         "stage": stage, "tabs": _tabs(stage), "editor_html": _editor_html(form)},
    )


def _neighbors(post):
    """같은 화면 목록(만든 순서, 최신이 위)에서 바로 위·아래 글."""
    same = Post.objects.filter(stage=post.stage)
    above = same.filter(
        Q(created_at__gt=post.created_at) | Q(created_at=post.created_at, pk__gt=post.pk)
    ).order_by("created_at", "pk").first()
    below = same.filter(
        Q(created_at__lt=post.created_at) | Q(created_at=post.created_at, pk__lt=post.pk)
    ).order_by("-created_at", "-pk").first()
    return above, below


def detail(request, pk):
    """글 보기: 블로그에 올라간 모습 그대로 보여 주고, 그대로 복사해 붙여넣게 한다."""
    post = get_object_or_404(Post, pk=pk)
    body_html = render_body(post.body)
    counted = plain_text(body_html, drop_slots=True)
    above, below = _neighbors(post)
    return render(
        request,
        "writing/detail.html",
        {
            "page_title": post.title,
            "post": post,
            "stage": post.stage,
            "tabs": _tabs(post.stage),
            "body_html": body_html,
            "body_text": plain_text(body_html),
            "chars": len(counted),
            "chars_no_space": len("".join(counted.split())),
            "slots": body_html.count('class="wr-slot"'),
            "above": above,
            "below": below,
            "next_label": {Stage.TEMP: "검토로", Stage.REVIEW: "포스트로"}.get(post.stage),
            "prev_label": {Stage.REVIEW: "임시로", Stage.POST: "검토로"}.get(post.stage),
            "review_choices": Post.Review.choices,
            "write_choices": Post.Write.choices,
            "publish_choices": Post.Publish.choices,
        },
    )


def edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = PostForm(request.POST or None, instance=post, stage=post.stage)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "저장했습니다.")
        return redirect(post)
    return render(
        request,
        "writing/form.html",
        {"page_title": post.title, "form": form, "post": post, "stage": post.stage, "tabs": _tabs(post.stage),
         "editor_html": _editor_html(form)},
    )


def _editor_html(form):
    """편집기(기본모드)에 처음 띄울 본문. 예전 마크다운 본문도 블로그 모양 HTML 로 바꿔서 연다."""
    body = form["body"].value() or ""
    return render_body(body) if body else ""


@require_POST
def convert(request):
    """편집기에 붙여넣은 것을 블로그 본문 HTML 로 바꾼다. kind: markdown | html | text"""
    kind, content = request.POST.get("kind", "text"), request.POST.get("content", "")
    if kind == "markdown":
        out = render_body(content)
    elif kind == "html":
        out = render_body(clean_html(content) or text_to_html(content))
    else:
        out = text_to_html(content)
    return JsonResponse({"html": out})


def delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == "POST":
        stage = post.stage
        post.delete()
        messages.success(request, "삭제했습니다.")
        return redirect(LIST_URLS[stage])
    return render(
        request,
        "writing/confirm_delete.html",
        {"page_title": "삭제", "post": post, "stage": post.stage, "tabs": _tabs(post.stage)},
    )


@require_POST
def move(request):
    """한 건(pk) 또는 체크한 여러 건(ids)을 이웃 화면으로 옮긴다."""
    to = request.POST.get("to", "")
    ids = request.POST.getlist("ids") or [request.POST.get("pk", "")]
    posts = Post.objects.filter(pk__in=[i for i in ids if i.isdigit()])
    moved, skipped, came_from = 0, 0, None
    for post in posts:
        came_from = came_from or post.stage
        if post.can_move_to(to):
            post.stage = to
            post.save(update_fields=["stage", "updated_at"])
            moved += 1
        else:
            skipped += 1
    if moved:
        messages.success(request, f"{moved}건을 {Stage(to).label}(으)로 옮겼습니다.")
    if skipped:
        messages.warning(request, f"{skipped}건은 옮길 수 없습니다. (발행 완료한 포스트는 되돌리지 않습니다)")
    if not moved and not skipped:
        messages.warning(request, "옮길 항목을 먼저 고르세요.")
    return _back(request, came_from or Stage.TEMP)


@require_POST
def set_status(request, pk):
    post = get_object_or_404(Post, pk=pk)
    field, value = request.POST.get("field", ""), request.POST.get("value", "")
    choices = STATUS_FIELDS.get(field)
    if choices is None or value not in choices.values:
        messages.warning(request, "바꿀 수 없는 상태입니다.")
        return _back(request, post.stage)
    setattr(post, field, value)
    update = [field, "updated_at"]
    if field == "publish_status" and value == Post.Publish.DONE and not post.published_on:
        post.published_on = timezone.localdate()
        update.append("published_on")
    post.save(update_fields=update)
    return _back(request, post.stage)
