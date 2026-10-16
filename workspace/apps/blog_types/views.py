"""글 매핑 관리 화면: 왼쪽 위 사이트 카테고리(2.5) · 아래 글 분류(7.5) + 오른쪽 목록.

- 사이트 카테고리 (왼쪽 위): 사이트(운영 화면의 블로그) › 카테고리 › 하위 카테고리. 누르면 그 카테고리에 넣은 글(매핑)이 보이고,
  포스트 관리까지 간 글을 골라 넣는다. 매핑마다 미저장 · 임시저장 · 발행.
- 글 분류 (왼쪽 아래): 티스토리 글쓰기 / 네이버 글쓰기 › 대분류 · 미분류 › 카테고리 › 타입 › 하위. 누르면 그 분류의 글(임시 → 검토 →
  포스트 전부)이 보이고, 포스트 관리 글은 그 자리에서 사이트 카테고리에 넣는다. 숫자는 그 아래 글 중 아직 발행 완료가 아닌 글 수.
  글쓰기마다 플랫폼이 맞는 카테고리만 (공통 + 그 플랫폼). 트리는 글 관리 화면과 같다 (classify.class_tree).

주소: ?sel=b2 (사이트) · k7 (사이트 카테고리) · ?w=tistory&sel=g1 (대분류) · c3 (카테고리) · t5 (타입) · s9 (하위) · u (미분류).
&edit=1 이면 고른 것의 이름·설명을 고치는 칸이 위에 열린다.
트리의 추가·수정·삭제는 각 트리 오른쪽 위 버튼으로 켠다 (켜야 행마다 +, 연필, 휴지통이 보인다).
"""
import string
from collections import Counter
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Max, Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.blog_rules.models import Blog

from . import classify
from .forms import FORMS
from .models import Category, Placement, PostType, Section, SiteCategory, SubType

MODELS = {"section": Section, "category": Category, "type": PostType, "sub": SubType,
          "site": Blog, "sitecat": SiteCategory}
PREFIX = {"g": "section", "c": "category", "t": "type", "s": "sub", "b": "site", "k": "sitecat"}
KIND_LABEL = {"section": "대분류", "category": "카테고리", "type": "타입", "sub": "하위",
              "site": "사이트", "sitecat": "사이트 카테고리", "unclassified": "분류"}
CHILD = {"section": "category", "category": "type", "type": "sub", "site": "sitecat"}
EDITABLE = {"section", "category", "type", "sub", "sitecat"}  # 사이트는 운영 화면에서 고친다
CLASS_KINDS = {"section", "category", "type", "sub", "unclassified"}


def _nav(request):
    request.nav_key = "blog_types"


def _writer(value):
    return value if value in classify.WRITERS else "tistory"


def _url(sel="", w="", edit=False):
    params = {k: v for k, v in (("w", w), ("sel", sel), ("edit", "1" if edit else "")) if v}
    base = reverse("blog_types:index")
    return f"{base}?{urlencode(params)}" if params else base


def _find(sel):
    if sel == "u":
        return "unclassified", classify.UNCLASSIFIED_NODE
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


def _chain(kind, obj):
    chain = []
    while obj is not None:
        chain.append(obj)
        kind, obj = _parent(kind, obj)
    return list(reversed(chain))


def _path(kind, obj, w):
    """고른 것까지의 경로: [(이름, 주소)]. 글 분류는 앞에 글쓰기 이름이 붙는다."""
    if kind == "unclassified":
        return [(classify.WRITERS[w], _url(w=w)), (obj.name, _url("u", w))]
    if kind in ("site", "sitecat"):
        return [(o.name, _url(o.sel)) for o in _chain(kind, obj)]
    return [(classify.WRITERS[w], _url(w=w))] + [
        (f"{o.code}. {o.name}" if isinstance(o, Category) else o.name, _url(o.sel, w)) for o in _chain(kind, obj)]


def _open_branches(kind, obj, w):
    """트리에서 펼쳐 둘 가지 (data-bt-branch 값)"""
    if kind in ("site", "sitecat"):
        return {o.sel for o in _chain(kind, obj)}
    if kind == "unclassified":
        return {w}
    return {w} | {f"{w}-{o.sel}" for o in _chain(kind, obj)}


def _child_kind(kind, obj):
    if kind == "sitecat":  # 사이트 카테고리는 2단까지 (티스토리·네이버 모두)
        return None if obj.parent_id else "sitecat"
    return CHILD.get(kind)


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


# ── 트리 ──────────────────────────────────────────────────────────

def _site_tree():
    counts = Counter(Placement.objects.values_list("site_category_id", flat=True))
    top = SiteCategory.objects.filter(parent=None).prefetch_related("children")
    sites = list(Blog.objects.prefetch_related(Prefetch("site_categories", queryset=top, to_attr="top_cats")))
    for b in sites:
        b.count = 0
        for c in b.top_cats:
            kids = list(c.children.all())
            for k in kids:
                k.count = counts[k.pk]
            c.count = counts[c.pk] + sum(k.count for k in kids)
            b.count += c.count
    return sites


# ── 오른쪽 목록 ──────────────────────────────────────────────────

def _placements_qs():
    return Placement.objects.select_related("site_category__blog", "site_category__parent",
                                            "tistory_post", "naver_post")


def _posts(w, kind, obj):
    """글 분류 한 단계 아래의 글 (임시·검토·포스트 모두) + 각 글을 넣은 사이트 카테고리"""
    qs = classify.post_model(w).objects.all()
    if kind in CLASS_KINDS:
        qs = qs.filter(classify.node_filter(kind, obj))
    qs = classify.with_classification(qs).prefetch_related(Prefetch("placements", queryset=_placements_qs()))
    posts = sorted(qs.order_by("-updated_at", "-pk"), key=classify.sort_key)
    for p in posts:
        p.cls_label = classify.label_of(p)
        p.step = "발행" if p.is_published else {"temp": "임시", "review": "검토", "post": "포스트"}[p.stage]
    return posts


def _site_options(w):
    """글 분류 쪽에서 글을 넣을 사이트 카테고리: 네이버 글은 네이버 사이트에, 티스토리 글은 그 밖의 사이트에"""
    blogs = Blog.objects.filter(platform=Blog.Platform.NAVER) if w == "naver" else Blog.objects.exclude(platform=Blog.Platform.NAVER)
    out = []
    for c in SiteCategory.objects.filter(blog__in=blogs, parent=None).select_related("blog").prefetch_related("children").order_by("blog__order", "order", "pk"):
        out.append((c.pk, f"{c.blog.name} › {c.name}"))
        out += [(k.pk, f"{c.blog.name} › {c.name} › {k.name}") for k in c.children.all()]
    return out


def _site_writer(blog):
    return "naver" if blog.platform == Blog.Platform.NAVER else "tistory"


def _candidates(cat):
    """이 사이트 카테고리에 넣을 수 있는 글: 맞는 글쓰기의 포스트 관리 글 중 아직 안 넣은 것"""
    w = _site_writer(cat.blog)
    field = "naver_post" if w == "naver" else "tistory_post"
    taken = Placement.objects.filter(site_category=cat, **{f"{field}__isnull": False}).values_list(f"{field}_id", flat=True)
    posts = classify.with_classification(classify.post_model(w).objects.filter(stage="post").exclude(pk__in=list(taken)))
    return [(p.pk, f"{p.title} — {classify.label_of(p)}") for p in sorted(posts.order_by("-updated_at"), key=classify.sort_key)]


def index(request, form=None):
    _nav(request)
    sel = request.GET.get("sel", "")
    w = request.GET.get("w", "")
    kind, obj = _find(sel)
    if obj is None:
        sel, kind = "", ("writer" if w in classify.WRITERS else None)
    w = _writer(w)
    editing = obj is not None and kind in EDITABLE and (request.GET.get("edit") == "1" or form is not None)
    if editing and form is None:
        form = FORMS[kind](instance=obj)
    ctx = {
        "page_title": "글 매핑 관리",
        "writers": classify.class_tree(),
        "sites": _site_tree(),
        "sel": sel, "w": w, "kind": kind, "obj": obj,
        "kind_label": {"writer": "글쓰기"}.get(kind, KIND_LABEL.get(kind, "")),
        "form": form if editing else None,
        "status_choices": Placement.Status.choices,
        "open": set(),
        "path": [],
    }
    if kind == "writer":
        ctx["path"] = [(classify.WRITERS[w], _url(w=w))]
        ctx["open"] = {w}
    elif obj is not None:
        ctx["path"] = _path(kind, obj, w)
        ctx["open"] = _open_branches(kind, obj, w)
    if kind == "writer" or kind in CLASS_KINDS:
        ctx["panel"] = "posts"
        ctx["posts"] = _posts(w, kind, obj)
        ctx["site_options"] = _site_options(w)
    elif kind in ("site", "sitecat"):
        ctx["panel"] = "places"
        cats = [obj] if kind == "sitecat" else list(obj.site_categories.all())
        if kind == "sitecat" and not obj.parent_id:
            cats += list(obj.children.all())
        ctx["placements"] = list(_placements_qs().filter(site_category__in=cats).order_by(
            "site_category__parent__order", "site_category__order", "created_at"))
        ctx["show_cat"] = len(cats) > 1
        if kind == "sitecat":
            ctx["candidates"] = _candidates(obj)
            ctx["site_writer"] = classify.WRITERS[_site_writer(obj.blog)]
    return render(request, "blog_types/index.html", ctx)


@require_POST
def save(request, kind, pk):
    if kind not in EDITABLE:
        raise Http404
    obj = get_object_or_404(MODELS[kind], pk=pk)
    form = FORMS[kind](request.POST, instance=obj)
    w = _writer(request.POST.get("w", ""))
    if form.is_valid():
        form.save()
        messages.success(request, "저장했습니다.")
        return redirect(_url(obj.sel, w if kind in CLASS_KINDS else ""))
    request.GET = request.GET.copy()
    request.GET.update({"sel": obj.sel, "w": w})
    return index(request, form=form)


@require_POST
def add(request, kind):
    """이름만으로 바로 추가하고, 추가한 것을 골라 둔다 (설명은 연필로 이어서 쓴다)."""
    name = " ".join(request.POST.get("name", "").split())
    parent_sel = request.POST.get("parent", "")
    w = _writer(request.POST.get("w", ""))
    back = _url(parent_sel, w if kind in CLASS_KINDS else "")
    if not name or kind not in EDITABLE:
        messages.warning(request, "이름을 입력하세요.")
        return redirect(back)
    if kind == "section":
        order = (Section.objects.aggregate(m=Max("order"))["m"] or 0) + 1
        obj = Section.objects.create(name=name[:40], order=order)
    else:
        parent_kind, parent = _find(parent_sel)
        if parent is None or _child_kind(parent_kind, parent) != kind:
            messages.warning(request, "어디에 추가할지 먼저 고르세요.")
            return redirect(back)
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
    return redirect(_url(obj.sel, w if kind in CLASS_KINDS else ""))


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
    return redirect(_url(obj.sel, _writer(request.POST.get("w", "")) if kind in CLASS_KINDS else "", edit=True))


def delete(request, kind, pk):
    _nav(request)
    if kind not in EDITABLE:
        raise Http404
    obj = get_object_or_404(MODELS[kind], pk=pk)
    _, parent = _parent(kind, obj)
    keep_w = _writer(request.GET.get("w", "")) if kind in CLASS_KINDS else ""
    if request.method == "POST":
        label = obj.name
        obj.delete()
        messages.success(request, f"{KIND_LABEL[kind]} '{label}'을(를) 삭제했습니다.")
        return redirect(_url(parent.sel, keep_w) if parent else _url())
    inside = []
    if kind == "section":
        inside = [f"카테고리 {obj.categories.count()}개", f"타입 {PostType.objects.filter(category__section=obj).count()}개",
                  f"하위 {SubType.objects.filter(post_type__category__section=obj).count()}개"]
    elif kind == "category":
        inside = [f"타입 {obj.types.count()}개", f"하위 {SubType.objects.filter(post_type__category=obj).count()}개"]
    elif kind == "type":
        inside = [f"하위 {obj.subs.count()}개"]
    elif kind == "sitecat":
        n = Placement.objects.filter(site_category__in=[obj, *obj.children.all()]).count()
        inside = ([f"하위 카테고리 {obj.children.count()}개"] if not obj.parent_id else []) + ([f"넣은 글 {n}개"] if n else [])
    return render(request, "blog_types/confirm_delete.html", {
        "page_title": "삭제", "obj": obj, "kind_label": KIND_LABEL[kind], "inside": inside,
        "back": _url(obj.sel, keep_w),
    })


# ── 매핑: 사이트 카테고리 ← 글 ─────────────────────────────────────

@require_POST
def place_add(request):
    cat = get_object_or_404(SiteCategory, pk=request.POST.get("site_category") or 0)
    w = _site_writer(cat.blog)
    post = classify.post_model(w).objects.filter(pk=request.POST.get("post") or 0, stage="post").first()
    status = request.POST.get("status") or Placement.Status.UNSAVED
    back = _url(cat.sel)
    if post is None or status not in Placement.Status.values:
        messages.warning(request, "넣을 글을 고르세요.")
        return _back(request, back)
    field = "naver_post" if w == "naver" else "tistory_post"
    if Placement.objects.filter(site_category=cat, **{field: post}).exists():
        messages.warning(request, "이미 넣은 글입니다.")
        return _back(request, back)
    Placement.objects.create(site_category=cat, status=status, **{field: post})
    messages.success(request, f"'{post.title}'을(를) {cat.blog.name} › {cat}에 넣었습니다.")
    return _back(request, back)


def _back(request, fallback):
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else fallback)


@require_POST
def place_status(request, pk):
    placement = get_object_or_404(Placement, pk=pk)
    status = request.POST.get("value")
    if status in Placement.Status.values and status != placement.status:
        placement.status = status
        placement.save(update_fields=["status", "updated_at"])
    return _back(request, _url(placement.site_category.sel))


@require_POST
def place_remove(request, pk):
    placement = get_object_or_404(Placement, pk=pk)
    sel = placement.site_category.sel
    placement.delete()
    messages.success(request, "사이트 카테고리에서 뺐습니다. 휴지통에서 7일 동안 되돌릴 수 있습니다.")
    return _back(request, _url(sel))
