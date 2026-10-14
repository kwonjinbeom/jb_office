from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.content.tree import decorate_tree, subtree_ids
from apps.content.navigation import list_return
from .forms import DiscussionForm, QuickForm
from .models import Discussion, DiscussionHistory


SNAPSHOT_FIELDS = ["summary", "next_action", "status", "amount", "partner"]


def save_form(form):
    with transaction.atomic():
        item = form.save()
        latest = item.history.first()
        snapshot = {field: getattr(item, field) for field in SNAPSHOT_FIELDS}
        if latest is None or any(getattr(latest, field) != value for field, value in snapshot.items()):
            DiscussionHistory.objects.create(discussion=item, **snapshot)
        return item


def discussion_list(request):
    nodes = decorate_tree(Discussion.objects.all())
    q, area, status = [request.GET.get(key, "").strip() for key in ("q", "area", "status")]
    selected = next((node for node in nodes if str(node.pk) == request.GET.get("topic") and (not area or node.area == area)), None)
    qs = Discussion.objects.all()
    if area in dict(Discussion.AREA_CHOICES):
        qs = qs.filter(area=area)
    if selected:
        qs = qs.filter(pk__in=subtree_ids(nodes, selected.pk))
    if status in Discussion.Status.values:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(summary__icontains=q) | Q(next_action__icontains=q))
    by_id = {node.pk: node for node in nodes}
    entries = list(qs)
    for entry in entries:
        entry.path = by_id[entry.pk].path
    return render(request, "discussions/list.html", {"page_title": "논의 현황", "entries": entries, "topics": [node for node in nodes if not area or node.area == area], "selected": selected, "q": q, "area": area, "status": status, "areas": Discussion.AREA_CHOICES, "statuses": Discussion.Status.choices})


def discussion_detail(request, pk):
    item = get_object_or_404(Discussion.objects.select_related("idea", "content"), pk=pk)
    nodes = decorate_tree(Discussion.objects.all())
    path = next(node.path for node in nodes if node.pk == pk)
    return render(request, "discussions/detail.html", {"page_title": item.name, "item": item, "path": path, "history": item.history.all(), "children": item.children.all()})


def discussion_form(request, pk=None):
    with transaction.atomic():
        item = get_object_or_404(Discussion.objects.select_for_update(), pk=pk) if pk else Discussion()
        initial = {}
        if not pk:
            parent = Discussion.objects.filter(pk=request.GET.get("parent")).first() if request.GET.get("parent", "").isdigit() else None
            if parent:
                initial.update(parent=parent, area=parent.area)
            elif request.GET.get("area") in dict(Discussion.AREA_CHOICES):
                initial["area"] = request.GET["area"]
        form = DiscussionForm(request.POST if request.method == "POST" else None, instance=item, initial=initial)
        if request.method == "POST" and form.is_valid():
            messages.success(request, "핵심을 저장했습니다.")
            return redirect(save_form(form))
    return render(request, "content/form.html", {"page_title": "논의 수정" if pk else "새 논의 주제", "form": form, "cancel_url": item.get_absolute_url() if pk else "/discussions/"})


@require_POST
def quick_update(request, pk):
    with transaction.atomic():
        item = get_object_or_404(Discussion.objects.select_for_update(), pk=pk)
        form = QuickForm(request.POST, instance=item)
        if form.is_valid():
            save_form(form)
        else:
            messages.error(request, "저장하지 못했습니다. 핵심은 140자, 다음 행동은 80자 이내로 적고 상태를 선택하세요.")
    return redirect(list_return(request, reverse("discussions:list")))


def discussion_delete(request, pk):
    item = get_object_or_404(Discussion, pk=pk)
    if request.method == "POST":
        try:
            item.delete()
        except ProtectedError:
            messages.error(request, "하위 주제를 먼저 옮기거나 삭제하세요.")
            return redirect(item)
        return redirect("discussions:list")
    return render(request, "content/delete.html", {"page_title": "논의 삭제", "object_title": item.name, "cancel_url": item.get_absolute_url()})
