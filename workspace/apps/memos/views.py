from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import Truncator

from .forms import MemoForm
from .models import Memo


def memo_list(request):
    q = request.GET.get("q", "").strip()
    qs = Memo.objects.all()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q) | Q(tags__icontains=q))
    return render(
        request,
        "memos/list.html",
        {"page_title": "메모", "memos": qs, "q": q, "total": Memo.objects.count()},
    )


def memo_detail(request, pk):
    memo = get_object_or_404(Memo, pk=pk)
    return render(request, "memos/detail.html", {"page_title": memo.title, "memo": memo})


def memo_create(request):
    form = MemoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        memo = form.save()
        messages.success(request, "메모를 추가했습니다.")
        return redirect(memo)
    return render(request, "memos/form.html", {"page_title": "새 메모", "form": form, "memo": None})


def memo_edit(request, pk):
    memo = get_object_or_404(Memo, pk=pk)
    form = MemoForm(request.POST or None, instance=memo)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "메모를 저장했습니다.")
        return redirect(memo)
    return render(request, "memos/form.html", {"page_title": "메모 수정", "form": form, "memo": memo})


def memo_delete(request, pk):
    memo = get_object_or_404(Memo, pk=pk)
    if request.method == "POST":
        memo.delete()
        messages.success(request, "메모를 휴지통으로 옮겼습니다.")
        return redirect("memos:list")
    return render(request, "core/confirm_delete.html", {
        "page_title": "메모 삭제", "kind_label": "메모", "object_label": memo.title, "cancel_url": memo.get_absolute_url(),
        "crumbs": [("메모", reverse("memos:list")), (Truncator(memo.title).chars(30), memo.get_absolute_url())]})


def memo_toggle_pin(request, pk):
    memo = get_object_or_404(Memo, pk=pk)
    if request.method == "POST":
        memo.pinned = not memo.pinned
        memo.save(update_fields=["pinned", "updated_at"])
    return redirect(request.POST.get("next") or "memos:list")
