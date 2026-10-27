from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.ideas.models import Idea, Stage

from .forms import EvidenceForm
from .models import Evidence


def evidence_list(request):
    q = request.GET.get("q", "").strip()
    kind = request.GET.get("kind", "")
    idea_id = request.GET.get("idea", "")
    qs = Evidence.objects.select_related("idea", "stage")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(url__icontains=q) | Q(note__icontains=q))
    if kind:
        qs = qs.filter(kind=kind)
    if idea_id:
        qs = qs.filter(idea_id=idea_id)
    return render(
        request,
        "evidence/list.html",
        {
            "page_title": "증거 수집함",
            "items": qs,
            "total": Evidence.objects.count(),
            "q": q,
            "kind": kind,
            "idea_id": idea_id,
            "kinds": Evidence.Kind.choices,
            "ideas": Idea.objects.only("id", "code", "title"),
            "is_filtered": bool(q or kind or idea_id),
        },
    )


def create(request):
    initial = {}
    if request.GET.get("idea"):
        initial["idea"] = Idea.objects.filter(pk=request.GET["idea"]).first()
    if request.GET.get("stage"):
        stage = Stage.objects.filter(pk=request.GET["stage"]).select_related("idea").first()
        if stage:
            initial["stage"] = stage
            initial["idea"] = stage.idea
    if request.GET.get("url"):
        initial["url"] = request.GET["url"]
    form = EvidenceForm(request.POST or None, initial=initial)
    _limit_stage_choices(form, initial.get("idea"))
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, "증거를 저장했습니다.")
        return redirect(request.POST.get("next") or _back(item))
    return render(
        request,
        "evidence/form.html",
        {"page_title": "증거 추가", "form": form, "item": None, "next": request.GET.get("next", "")},
    )


def edit(request, pk):
    item = get_object_or_404(Evidence, pk=pk)
    form = EvidenceForm(request.POST or None, instance=item)
    _limit_stage_choices(form, item.idea)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "증거를 저장했습니다.")
        return redirect(request.POST.get("next") or _back(item))
    return render(
        request,
        "evidence/form.html",
        {"page_title": "증거 수정", "form": form, "item": item, "next": request.GET.get("next", "")},
    )


def delete(request, pk):
    item = get_object_or_404(Evidence, pk=pk)
    if request.method == "POST":
        back = _back(item)
        item.delete()
        messages.success(request, "증거를 휴지통으로 옮겼습니다.")
        return redirect(back)
    return render(
        request,
        "core/confirm_delete.html",
        {"page_title": "증거 삭제", "object_label": item.display_title, "cancel_url": _back(item)},
    )


def _limit_stage_choices(form: EvidenceForm, idea) -> None:
    if idea is not None:
        form.fields["stage"].queryset = Stage.objects.filter(idea=idea)


def _back(item: Evidence) -> str:
    if item.idea_id:
        return item.idea.get_absolute_url()
    return "/evidence/"
