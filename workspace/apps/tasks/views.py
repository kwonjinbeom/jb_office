from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.ideas.models import Idea, Stage

from .forms import QuickTaskForm, TaskForm
from .models import Task


def task_list(request):
    today = timezone.localdate()
    open_qs = list(Task.objects.filter(done=False).select_related("idea", "stage"))
    groups = [
        ("지남", [t for t in open_qs if t.due and t.due < today]),
        ("오늘", [t for t in open_qs if t.due == today]),
        ("예정", [t for t in open_qs if t.due and t.due > today]),
        ("마감 없음", [t for t in open_qs if not t.due]),
    ]
    done_qs = Task.objects.filter(done=True).select_related("idea", "stage").order_by("-done_at")[:30]
    return render(
        request,
        "tasks/list.html",
        {
            "page_title": "할 일",
            "groups": groups,
            "open_count": len(open_qs),
            "done_tasks": done_qs,
            "quick_form": QuickTaskForm(),
        },
    )


@require_POST
def quick_add(request):
    form = QuickTaskForm(request.POST)
    if form.is_valid():
        Task.objects.create(title=form.cleaned_data["title"], due=form.cleaned_data["due"])
    else:
        messages.error(request, "할 일 제목이 비어 있습니다.")
    return redirect("tasks:list")


def create(request):
    initial = {}
    if request.GET.get("idea"):
        initial["idea"] = Idea.objects.filter(pk=request.GET["idea"]).first()
    if request.GET.get("stage"):
        stage = Stage.objects.filter(pk=request.GET["stage"]).select_related("idea").first()
        if stage:
            initial["stage"] = stage
            initial["idea"] = stage.idea
    form = TaskForm(request.POST or None, initial=initial)
    _limit_stage_choices(form, initial.get("idea"))
    if request.method == "POST" and form.is_valid():
        task = form.save()
        messages.success(request, "할 일을 추가했습니다.")
        return redirect(request.POST.get("next") or _back(task))
    return render(
        request,
        "tasks/form.html",
        {"page_title": "할 일 추가", "form": form, "task": None, "next": request.GET.get("next", "")},
    )


def edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    form = TaskForm(request.POST or None, instance=task)
    _limit_stage_choices(form, task.idea)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        if task.done and not task.done_at:
            task.done_at = timezone.now()
        if not task.done:
            task.done_at = None
        task.save()
        messages.success(request, "할 일을 저장했습니다.")
        return redirect(request.POST.get("next") or _back(task))
    return render(
        request,
        "tasks/form.html",
        {"page_title": "할 일 수정", "form": form, "task": task, "next": request.GET.get("next", "")},
    )


def delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == "POST":
        back = _back(task)
        task.delete()
        messages.success(request, "할 일을 삭제했습니다.")
        return redirect(back)
    return render(
        request,
        "core/confirm_delete.html",
        {"page_title": "할 일 삭제", "object_label": task.title, "cancel_url": _back(task)},
    )


@require_POST
def toggle(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.set_done(not task.done)
    return redirect(request.POST.get("next") or "tasks:list")


def _limit_stage_choices(form: TaskForm, idea) -> None:
    """단계 선택지는 해당 아이디어의 단계만 보여 준다. 아이디어가 없으면 전체."""
    if idea is not None:
        form.fields["stage"].queryset = Stage.objects.filter(idea=idea)


def _back(task: Task) -> str:
    if task.idea_id:
        return task.idea.get_absolute_url()
    return "/tasks/"
