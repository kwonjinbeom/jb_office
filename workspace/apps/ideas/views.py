from django.contrib import messages
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import IdeaForm, LogForm, QuickStageForm, StageForm
from .models import Idea, IdeaLog, Stage

# 표의 열. (키, 제목, 정렬 필드)
COLUMNS = [
    ("code", "코드", "code"),
    ("title", "제목", "title"),
    ("category", "분류", "category"),
    ("status", "상태", "status"),
    ("priority", "우선순위", "priority"),
    ("customer", "고객", "customer"),
    ("judgement", "현재 판단", "judgement"),
    ("updated", "수정", "updated_at"),
]
SORT_FIELDS = {key: field for key, _, field in COLUMNS}


def idea_list(request):
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")

    sort = request.GET.get("sort", "code")
    sort_desc = sort.startswith("-")
    sort_key = sort.lstrip("-")
    if sort_key not in SORT_FIELDS:
        sort_key, sort_desc = "code", False
    order = ("-" if sort_desc else "") + SORT_FIELDS[sort_key]

    qs = Idea.objects.all()
    if q:
        qs = qs.filter(
            Q(code__icontains=q)
            | Q(title__icontains=q)
            | Q(customer__icontains=q)
            | Q(pain__icontains=q)
            | Q(judgement__icontains=q)
            | Q(tags__icontains=q)
        )
    if category:
        qs = qs.filter(category=category)
    if status:
        qs = qs.filter(status=status)
    qs = qs.order_by(order, "code").prefetch_related("stages")

    context = {
        "page_title": "아이디어",
        "ideas": qs,
        "total": Idea.objects.count(),
        "q": q,
        "category": category,
        "status": status,
        "sort": ("-" if sort_desc else "") + sort_key,
        "sort_key": sort_key,
        "sort_desc": sort_desc,
        "columns": [(key, label) for key, label, _ in COLUMNS],
        "categories": Idea.Category.choices,
        "statuses": Idea.Status.choices,
        "is_filtered": bool(q or category or status),
    }
    return render(request, "ideas/list.html", context)


def idea_detail(request, pk):
    idea = get_object_or_404(Idea.objects.prefetch_related("stages"), pk=pk)
    fields = [
        ("고객·독자", idea.customer),
        ("불편·욕구", idea.pain),
        ("현재 지출·대안", idea.current_alternative),
        ("돈이 생기는 방식", idea.money_flow),
        ("증거·수요 신호", idea.evidence),
        ("최소 판매물·공개물", idea.min_product),
        ("첫 고객·유통 경로", idea.channel),
        ("핵심 위험", idea.risk),
        ("현재 판단", idea.judgement),
    ]
    prev_idea = Idea.objects.filter(code__lt=idea.code).order_by("-code").first()
    next_idea = Idea.objects.filter(code__gt=idea.code).order_by("code").first()
    stages = list(idea.stages.all())
    done, total = idea.stage_progress
    return render(
        request,
        "ideas/detail.html",
        {
            "page_title": f"{idea.code} {idea.title}",
            "idea": idea,
            "fields": fields,
            "prev_idea": prev_idea,
            "next_idea": next_idea,
            "stages": stages,
            "current_stage": idea.current_stage,
            "progress": {"done": done, "total": total, "pct": int(done * 100 / total) if total else 0},
            "tasks": idea.tasks.select_related("stage").order_by("done", "due", "-created_at"),
            "evidence_items": idea.links.select_related("stage").order_by("-captured_at"),
            "logs": idea.logs.select_related("stage")[:30],
            "log_form": LogForm(idea=idea),
            "quick_stage_form": QuickStageForm(),
        },
    )


def idea_create(request):
    form = IdeaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        idea = form.save()
        messages.success(request, f"{idea.code} 아이디어를 추가했습니다.")
        return redirect(idea)
    return render(request, "ideas/form.html", {"page_title": "아이디어 추가", "form": form, "idea": None})


def idea_edit(request, pk):
    idea = get_object_or_404(Idea, pk=pk)
    form = IdeaForm(request.POST or None, instance=idea)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{idea.code} 아이디어를 저장했습니다.")
        return redirect(idea)
    return render(request, "ideas/form.html", {"page_title": f"{idea.code} 수정", "form": form, "idea": idea})


def idea_delete(request, pk):
    idea = get_object_or_404(Idea, pk=pk)
    if request.method == "POST":
        code = idea.code
        idea.delete()
        messages.success(request, f"{code} 아이디어를 삭제했습니다.")
        return redirect("ideas:list")
    return render(request, "ideas/confirm_delete.html", {"page_title": f"{idea.code} 삭제", "idea": idea})


# ---- 단계 ------------------------------------------------------------------


@require_POST
def stage_quick_add(request, pk):
    idea = get_object_or_404(Idea, pk=pk)
    form = QuickStageForm(request.POST)
    if form.is_valid():
        last = idea.stages.aggregate(m=Max("order"))["m"] or 0
        Stage.objects.create(idea=idea, order=last + 1, title=form.cleaned_data["title"])
    return redirect(f"{idea.get_absolute_url()}#stages")


def stage_edit(request, pk, stage_pk):
    idea = get_object_or_404(Idea, pk=pk)
    stage = get_object_or_404(Stage, pk=stage_pk, idea=idea)
    form = StageForm(request.POST or None, instance=stage)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"단계 '{stage.title}' 을 저장했습니다.")
        return redirect(f"{idea.get_absolute_url()}#stages")
    return render(
        request,
        "ideas/stage_form.html",
        {"page_title": f"{idea.code} · 단계 수정", "idea": idea, "stage": stage, "form": form},
    )


@require_POST
def stage_set_status(request, pk, stage_pk):
    idea = get_object_or_404(Idea, pk=pk)
    stage = get_object_or_404(Stage, pk=stage_pk, idea=idea)
    status = request.POST.get("status")
    if status in Stage.Status.values:
        if status == Stage.Status.DOING:
            # 진행 중은 한 번에 하나만. 다른 진행 단계는 대기로 돌린다.
            idea.stages.filter(status=Stage.Status.DOING).exclude(pk=stage.pk).update(status=Stage.Status.TODO)
        stage.status = status
        stage.save(update_fields=["status", "updated_at"])
    return redirect(f"{idea.get_absolute_url()}#stages")


@require_POST
def stage_move(request, pk, stage_pk):
    idea = get_object_or_404(Idea, pk=pk)
    stages = list(idea.stages.all())
    idx = next((i for i, s in enumerate(stages) if s.pk == stage_pk), None)
    if idx is not None:
        swap = idx - 1 if request.POST.get("dir") == "up" else idx + 1
        if 0 <= swap < len(stages):
            stages[idx], stages[swap] = stages[swap], stages[idx]
            for i, s in enumerate(stages, start=1):
                if s.order != i:
                    s.order = i
                    s.save(update_fields=["order"])
    return redirect(f"{idea.get_absolute_url()}#stages")


@require_POST
def stage_delete(request, pk, stage_pk):
    idea = get_object_or_404(Idea, pk=pk)
    stage = get_object_or_404(Stage, pk=stage_pk, idea=idea)
    stage.delete()
    messages.success(request, "단계를 삭제했습니다.")
    return redirect(f"{idea.get_absolute_url()}#stages")


# ---- 작업 로그 ---------------------------------------------------------------


@require_POST
def log_add(request, pk):
    idea = get_object_or_404(Idea, pk=pk)
    form = LogForm(request.POST, idea=idea)
    if form.is_valid():
        log = form.save(commit=False)
        log.idea = idea
        log.save()
    else:
        messages.error(request, "로그 내용이 비어 있습니다.")
    return redirect(f"{idea.get_absolute_url()}#logs")


@require_POST
def log_delete(request, pk, log_pk):
    idea = get_object_or_404(Idea, pk=pk)
    IdeaLog.objects.filter(pk=log_pk, idea=idea).delete()
    return redirect(f"{idea.get_absolute_url()}#logs")
