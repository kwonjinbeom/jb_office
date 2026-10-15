"""타입·카테고리 화면: 왼쪽 트리(카테고리 › 타입 › 하위) + 오른쪽 상세.

한 화면에서 고른다: ?sel=c3 (카테고리) · t5 (타입) · s9 (하위).
트리에는 이름과 하위 개수만, 설명은 고른 뒤 오른쪽에서 본다.
"""
import string

from django.contrib import messages
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import FORMS
from .models import Category, PostType, SubType

MODELS = {"category": Category, "type": PostType, "sub": SubType}
PREFIX = {"c": "category", "t": "type", "s": "sub"}
KIND_LABEL = {"category": "카테고리", "type": "타입", "sub": "하위"}
CHILD = {"category": "type", "type": "sub"}


def _nav(request):
    request.nav_key = "blog_types"


def _url(sel=""):
    base = reverse("blog_types:index")
    return f"{base}?sel={sel}" if sel else base


def _find(sel):
    kind = PREFIX.get((sel or "")[:1])
    pk = (sel or "")[1:]
    if not kind or not pk.isdigit():
        return None, None
    return kind, MODELS[kind].objects.filter(pk=pk).first()


def _parent(kind, obj):
    if kind == "type":
        return obj.category
    if kind == "sub":
        return obj.post_type
    return None


def _path(kind, obj):
    """고른 것까지의 경로: [(이름, sel)] — 카테고리 › 타입 › 하위"""
    chain = []
    while obj is not None:
        chain.append(obj)
        obj = _parent(kind, obj)
        kind = {"sub": "type", "type": "category"}.get(kind)
    return [(f"{o.code}. {o.name}" if isinstance(o, Category) else o.name, o.sel) for o in reversed(chain)]


def _siblings(kind, obj):
    if kind == "category":
        return Category.objects.all()
    if kind == "type":
        return obj.category.types.all()
    return obj.post_type.subs.all()


def _children(kind, obj):
    if kind == "category":
        return obj.types.all()
    if kind == "type":
        return obj.subs.all()
    return []


def index(request, form=None):
    _nav(request)
    sel = request.GET.get("sel", "")
    kind, obj = _find(sel)
    if obj is None:
        sel, kind = "", None
    if obj is not None and form is None:
        form = FORMS[kind](instance=obj)
    return render(request, "blog_types/index.html", {
        "page_title": "타입·카테고리",
        "categories": Category.objects.prefetch_related("types__subs"),
        "sel": sel,
        "kind": kind,
        "obj": obj,
        "kind_label": KIND_LABEL.get(kind, ""),
        "form": form,
        "path": _path(kind, obj) if obj else [],
        "children": _children(kind, obj) if obj else [],
        "child_kind": CHILD.get(kind),
        "child_label": KIND_LABEL.get(CHILD.get(kind), ""),
        "counts": {
            "category": Category.objects.count(),
            "type": PostType.objects.count(),
            "sub": SubType.objects.count(),
        },
    })


@require_POST
def save(request, kind, pk):
    obj = get_object_or_404(MODELS[kind], pk=pk)
    form = FORMS[kind](request.POST, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, "저장했습니다.")
        return redirect(_url(obj.sel))
    request.GET = request.GET.copy()
    request.GET["sel"] = obj.sel
    return index(request, form=form)


@require_POST
def add(request, kind):
    """이름만으로 바로 추가하고, 추가한 것을 골라 둔다 (설명은 오른쪽에서 이어서 쓴다)."""
    name = " ".join(request.POST.get("name", "").split())
    parent_sel = request.POST.get("parent", "")
    if not name or kind not in MODELS:
        messages.warning(request, "이름을 입력하세요.")
        return redirect(_url(parent_sel))
    if kind == "category":
        used = set(Category.objects.values_list("code", flat=True))
        code = next((c for c in string.ascii_uppercase if c not in used), "?")
        order = (Category.objects.aggregate(m=Max("order"))["m"] or 0) + 1
        obj = Category.objects.create(code=code, name=name[:40], order=order)
    else:
        parent_kind, parent = _find(parent_sel)
        if parent is None or CHILD.get(parent_kind) != kind:
            messages.warning(request, "어디에 추가할지 먼저 고르세요.")
            return redirect(_url())
        order = (_children(parent_kind, parent).aggregate(m=Max("order"))["m"] or 0) + 1
        if kind == "type":
            obj = PostType.objects.create(category=parent, name=name[:60], order=order)
        else:
            obj = SubType.objects.create(post_type=parent, name=name[:80], order=order)
    messages.success(request, f"{KIND_LABEL[kind]} '{obj.name}'을(를) 추가했습니다.")
    return redirect(_url(obj.sel))


@require_POST
def move(request, kind, pk):
    obj = get_object_or_404(MODELS[kind], pk=pk)
    items = list(_siblings(kind, obj))
    i = items.index(obj)
    j = i - 1 if request.POST.get("dir") == "up" else i + 1
    if 0 <= j < len(items):
        items[i], items[j] = items[j], items[i]
        for n, item in enumerate(items, start=1):  # 순서를 1, 2, 3 … 으로 다시 매긴다
            if item.order != n:
                item.order = n
                item.save(update_fields=["order"])
    return redirect(_url(request.POST.get("back") or obj.sel))


def delete(request, kind, pk):
    _nav(request)
    obj = get_object_or_404(MODELS[kind], pk=pk)
    parent = _parent(kind, obj)
    if request.method == "POST":
        label = obj.name
        obj.delete()
        messages.success(request, f"{KIND_LABEL[kind]} '{label}'을(를) 삭제했습니다.")
        return redirect(_url(parent.sel if parent else ""))
    inside = []
    if kind == "category":
        inside = [f"타입 {obj.types.count()}개", f"하위 {SubType.objects.filter(post_type__category=obj).count()}개"]
    elif kind == "type":
        inside = [f"하위 {obj.subs.count()}개"]
    return render(request, "blog_types/confirm_delete.html", {
        "page_title": "삭제", "obj": obj, "kind_label": KIND_LABEL[kind], "inside": inside,
        "back": _url(obj.sel),
    })
