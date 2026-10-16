"""타입·카테고리 화면: 트리 두 개 + 오른쪽 상세.

- 글 분류: 대분류 › 카테고리 › 타입 › 하위
- 사이트 카테고리: 사이트(운영 화면의 블로그) › 카테고리 › 하위 카테고리 — 각 블로그에 실제로 있는 메뉴 이름

한 화면에서 고른다: ?sel=g1 (대분류) · c3 (카테고리) · t5 (타입) · s9 (하위) · b2 (사이트) · k7 (사이트 카테고리).
트리에는 이름과 하위 개수만, 설명은 고른 뒤 오른쪽에서 본다. 사이트 자체는 운영 화면에서 고친다.
"""
import string

from django.contrib import messages
from django.db.models import Max, Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.blog_rules.models import Blog

from .forms import FORMS
from .models import Category, PostType, Section, SiteCategory, SubType

MODELS = {"section": Section, "category": Category, "type": PostType, "sub": SubType,
          "site": Blog, "sitecat": SiteCategory}
PREFIX = {"g": "section", "c": "category", "t": "type", "s": "sub", "b": "site", "k": "sitecat"}
KIND_LABEL = {"section": "대분류", "category": "카테고리", "type": "타입", "sub": "하위",
              "site": "사이트", "sitecat": "사이트 카테고리"}
CHILD = {"section": "category", "category": "type", "type": "sub", "site": "sitecat"}
EDITABLE = {"section", "category", "type", "sub", "sitecat"}  # 사이트는 운영 화면에서 고친다


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
    """(윗단계 kind, 윗단계)"""
    if kind == "category":
        return "section", obj.section
    if kind == "type":
        return "category", obj.category
    if kind == "sub":
        return "type", obj.post_type
    if kind == "sitecat":
        return ("sitecat", obj.parent) if obj.parent_id else ("site", obj.blog)
    return None, None


def _path(kind, obj):
    """고른 것까지의 경로: [(이름, sel)] — 카테고리 › 타입 › 하위"""
    chain = []
    while obj is not None:
        chain.append(obj)
        kind, obj = _parent(kind, obj)
    return [(f"{o.code}. {o.name}" if isinstance(o, Category) else o.name, o.sel) for o in reversed(chain)]


def _child_kind(kind, obj):
    if kind == "sitecat":  # 사이트 카테고리는 2단까지 (티스토리·네이버 모두)
        return None if obj.parent_id else "sitecat"
    return CHILD.get(kind)


def _child_label(kind):
    if kind == "site":
        return "카테고리"
    if kind == "sitecat":
        return "하위 카테고리"
    return KIND_LABEL.get(CHILD.get(kind), "")


def _siblings(kind, obj):
    if kind == "section":
        return Section.objects.all()
    if kind == "category":
        return obj.section.categories.all()
    if kind == "type":
        return obj.category.types.all()
    if kind == "sitecat":
        return SiteCategory.objects.filter(blog=obj.blog, parent=obj.parent)
    return obj.post_type.subs.all()


def _children(kind, obj):
    if kind == "section":
        return obj.categories.all()
    if kind == "category":
        return obj.types.all()
    if kind == "type":
        return obj.subs.all()
    if kind == "site":
        return obj.site_categories.filter(parent=None)
    return obj.children.all()


def index(request, form=None):
    _nav(request)
    sel = request.GET.get("sel", "")
    kind, obj = _find(sel)
    if obj is None:
        sel, kind = "", None
    if obj is not None and form is None and kind in EDITABLE:
        form = FORMS[kind](instance=obj)
    child_kind = _child_kind(kind, obj) if obj else None
    top_cats = SiteCategory.objects.filter(parent=None).prefetch_related("children")
    return render(request, "blog_types/index.html", {
        "page_title": "타입·카테고리",
        "sections": Section.objects.prefetch_related("categories__types__subs"),
        "sites": Blog.objects.prefetch_related(Prefetch("site_categories", queryset=top_cats, to_attr="top_cats")),
        "open": {s for _, s in (_path(kind, obj) if obj else [])},  # 고른 것의 윗단계는 펼쳐 둔다
        "sel": sel,
        "kind": kind,
        "obj": obj,
        "kind_label": KIND_LABEL.get(kind, ""),
        "form": form,
        "path": _path(kind, obj) if obj else [],
        "children": _children(kind, obj) if child_kind else [],
        "child_kind": child_kind,
        "child_label": _child_label(kind) if obj else "",
        "counts": {
            "section": Section.objects.count(),
            "category": Category.objects.count(),
            "type": PostType.objects.count(),
            "sub": SubType.objects.count(),
            "sitecat": SiteCategory.objects.count(),
        },
    })


@require_POST
def save(request, kind, pk):
    if kind not in EDITABLE:
        raise Http404
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
    if not name or kind not in EDITABLE:
        messages.warning(request, "이름을 입력하세요.")
        return redirect(_url(parent_sel))
    if kind == "section":
        order = (Section.objects.aggregate(m=Max("order"))["m"] or 0) + 1
        obj = Section.objects.create(name=name[:40], order=order)
    else:
        parent_kind, parent = _find(parent_sel)
        if parent is None or _child_kind(parent_kind, parent) != kind:
            messages.warning(request, "어디에 추가할지 먼저 고르세요.")
            return redirect(_url(parent_sel if parent is not None else ""))
        order = (_children(parent_kind, parent).aggregate(m=Max("order"))["m"] or 0) + 1
        if kind == "sitecat":
            blog = parent if parent_kind == "site" else parent.blog
            obj = SiteCategory.objects.create(blog=blog, parent=None if parent_kind == "site" else parent,
                                              name=name[:60], order=order)
        elif kind == "category":
            used = set(Category.all_objects.filter(section=parent).values_list("code", flat=True))
            code = next((c for c in string.ascii_uppercase if c not in used), "?")
            obj = Category.objects.create(section=parent, code=code, name=name[:40], order=order)
        elif kind == "type":
            obj = PostType.objects.create(category=parent, name=name[:60], order=order)
        else:
            obj = SubType.objects.create(post_type=parent, name=name[:80], order=order)
    messages.success(request, f"{KIND_LABEL[kind]} '{obj.name}'을(를) 추가했습니다.")
    return redirect(_url(obj.sel))


@require_POST
def move(request, kind, pk):
    if kind not in EDITABLE:
        raise Http404
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
    if kind not in EDITABLE:
        raise Http404
    obj = get_object_or_404(MODELS[kind], pk=pk)
    _, parent = _parent(kind, obj)
    if request.method == "POST":
        label = obj.name
        obj.delete()
        messages.success(request, f"{KIND_LABEL[kind]} '{label}'을(를) 삭제했습니다.")
        return redirect(_url(parent.sel if parent else ""))
    inside = []
    if kind == "section":
        inside = [f"카테고리 {obj.categories.count()}개", f"타입 {PostType.objects.filter(category__section=obj).count()}개",
                  f"하위 {SubType.objects.filter(post_type__category__section=obj).count()}개"]
    elif kind == "category":
        inside = [f"타입 {obj.types.count()}개", f"하위 {SubType.objects.filter(post_type__category=obj).count()}개"]
    elif kind == "type":
        inside = [f"하위 {obj.subs.count()}개"]
    elif kind == "sitecat" and not obj.parent_id:
        inside = [f"하위 카테고리 {obj.children.count()}개"]
    return render(request, "blog_types/confirm_delete.html", {
        "page_title": "삭제", "obj": obj, "kind_label": KIND_LABEL[kind], "inside": inside,
        "back": _url(obj.sel),
    })
