from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import IdeaForm
from .models import Idea

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
    qs = qs.order_by(order, "code")

    context = {
        "page_title": "아이디어 리스트",
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
    idea = get_object_or_404(Idea, pk=pk)
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
    return render(
        request,
        "ideas/detail.html",
        {
            "page_title": f"{idea.code} {idea.title}",
            "idea": idea,
            "fields": fields,
            "prev_idea": prev_idea,
            "next_idea": next_idea,
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
    return render(
        request, "ideas/form.html", {"page_title": f"{idea.code} 수정", "form": form, "idea": idea}
    )


def idea_delete(request, pk):
    idea = get_object_or_404(Idea, pk=pk)
    if request.method == "POST":
        code = idea.code
        idea.delete()
        messages.success(request, f"{code} 아이디어를 삭제했습니다.")
        return redirect("ideas:list")
    return render(request, "ideas/confirm_delete.html", {"page_title": f"{idea.code} 삭제", "idea": idea})
