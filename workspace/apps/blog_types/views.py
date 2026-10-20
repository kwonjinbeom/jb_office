"""글 매핑 관리 화면: 트리 두 칸(사이트 카테고리 · 글 분류) + 오른쪽에 두 목록을 함께 (위 2.5 · 아래 7.5).

- 사이트 카테고리 (왼쪽): 사이트(운영 화면의 블로그) › 카테고리 › 하위 카테고리. 누르면 오른쪽 **위** 목록이 그 카테고리에 넣은 글(매핑)로
  바뀐다. 아무것도 안 고르면 모든 매핑. 매핑마다 발행 상태(미발행 → 발행 완료, 사용자가 직접 올리고 바꾼다)와 변환 상태.
- 글 분류 (가운데): 모든 글 › 대분류 · 미분류 › 카테고리 › 타입 › 하위 (티스토리·네이버 나눔 없음). 누르면 오른쪽 **아래** 목록이
  그 분류의 발행예정글로 바뀌고 (2026-10-17 사용자: 아래는 발행예정글만, 사이트 칸, 오늘·사이트 조건), 그 자리에서 사이트 카테고리에 넣는다.
  사이트·플랫폼에 맞추는 일은 마지막 단계(사이트별 템플릿의 변환)에서 한다. 숫자는 발행 완료가 아닌 글 수.

주소: ?site=b2|k7 (위) &sel=g1|c3|t5|s9|u (아래) &today=1 &psite=<사이트 이름>|- (아래 조건) &edit=<고칠 것의 sel>.
두 고르기와 아래 조건은 서로 유지된다.
트리를 누르면 화면 전체를 새로 받지 않고 그 목록 칸만 바꾼다 (요청 머리 X-Partial: top|bottom → 그 칸 HTML 만 돌려준다).
예전 주소 ?sel=k7 (사이트 카테고리) 도 위 목록으로 받는다.
트리의 추가·수정·삭제는 각 트리 오른쪽 위 버튼으로 켠다 (켜야 행마다 +, 연필, 휴지통이 보인다).
"""
import string
from collections import Counter
from urllib.parse import parse_qsl, urlencode, urlsplit

from django.contrib import messages
from django.db.models import Max, Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog_rules.models import Blog

from . import classify, sites
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
SITE_KINDS = {"site", "sitecat"}


def _nav(request):
    request.nav_key = "blog_types"


def _writer(value):
    return value if value in classify.WRITERS else "tistory"


def _is_site(sel):
    return (sel or "")[:1] in ("b", "k")


def _url(sel="", w="", edit=False):
    """한쪽만 고른 주소. 사이트 쪽 값은 site, 글 분류 쪽 값은 w·sel 로 간다."""
    params = {}
    if _is_site(sel):
        params["site"] = sel
    elif sel:
        params["sel"] = sel
    if edit and sel:
        params["edit"] = sel
    base = reverse("blog_types:index")
    return f"{base}?{urlencode(params)}" if params else base


def _merge(base, sel="", w="", edit=""):
    """지금 보던 주소(base)에서 한쪽 고르기만 바꾼다. 다른 쪽 고르기는 그대로 둔다. 고치기(edit)는 지운다."""
    index = reverse("blog_types:index")
    parts = urlsplit(base or index)
    params = dict(parse_qsl(parts.query)) if parts.path == index else {}
    params.pop("edit", None)
    params.pop("w", None)  # 예전 주소의 글쓰기 나눔
    if sel:
        if _is_site(sel):
            params["site"] = sel
        else:
            params["sel"] = sel
    if edit:
        params["edit"] = edit
    return f"{index}?{urlencode(params)}" if params else index


def _next(request):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else ""


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


ALL_POSTS = "모든 글"


def _path(kind, obj, w=""):
    """고른 것까지의 경로: [(이름, 주소)]. 글 분류는 앞에 '모든 글'이 붙는다."""
    if kind in SITE_KINDS:
        return [(o.name, _url(o.sel)) for o in _chain(kind, obj)]
    root = [(ALL_POSTS, reverse("blog_types:index") + "?")]
    if kind == "unclassified":
        return root + [(obj.name, _url("u"))]
    if kind not in CLASS_KINDS:
        return root
    return root + [(f"{o.code}. {o.name}" if isinstance(o, Category) else o.name, _url(o.sel)) for o in _chain(kind, obj)]


def _open_branches(kind, obj, w=""):
    """트리에서 펼쳐 둘 가지 (data-bt-branch 값)"""
    if kind in SITE_KINDS or kind in CLASS_KINDS - {"unclassified"}:
        return {o.sel for o in _chain(kind, obj)}
    return set()


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


NO_SITE = "-"  # 아래 조건: 사이트를 아직 안 고른 글


def _posts(kind, obj, today=False, psite=""):
    """글 분류 한 단계 아래의 발행예정글 (두 편집기의 글 모두) + 각 글을 넣은 사이트 카테고리.
    today: 오늘 만든 글만 (글 관리의 '오늘'과 같다). psite: 그 사이트 글만 ('-' 는 사이트 없는 글)."""
    def narrow(qs):
        qs = qs.filter(stage="post")
        if kind in CLASS_KINDS:
            qs = qs.filter(classify.node_filter(kind, obj))
        if today:
            qs = qs.filter(created_at__date=timezone.localdate())
        if psite:
            qs = qs.filter(target="" if psite == NO_SITE else psite)
        return classify.with_classification(qs).prefetch_related(Prefetch("placements", queryset=_placements_qs()))
    posts = classify.all_posts(narrow)
    posts.sort(key=lambda p: (p.updated_at, p.pk), reverse=True)
    posts.sort(key=classify.sort_key)
    groups = _site_groups()
    for p in posts:
        p.cls_label = classify.label_of(p)
        p.site_groups = sorted(groups, key=lambda g: g[0] != p.target)  # 그 글의 사이트를 맨 위에
    return posts


def _site_groups():
    """글을 넣을 사이트 카테고리를 사이트마다 묶어서: [(사이트 이름, [(pk, 이름)])]. 카테고리 없는 사이트는 뺀다."""
    groups = {}
    for c in SiteCategory.objects.filter(parent=None).select_related("blog").prefetch_related("children").order_by("blog__order", "order", "pk"):
        rows = groups.setdefault(c.blog.name, [])
        rows.append((c.pk, c.name))
        rows += [(k.pk, f"{c.name} › {k.name}") for k in c.children.all()]
    return list(groups.items())


def _site_writer(blog):
    return "naver" if blog.platform == Blog.Platform.NAVER else "tistory"


FIELD = {"tistory": "tistory_post", "naver": "naver_post"}


def _candidates(cat):
    """이 사이트 카테고리에 넣을 수 있는 글: 발행예정글 중 아직 안 넣은 것 (두 편집기의 글 모두). 값은 'tistory:3' 꼴."""
    taken = {(w, pk) for w in FIELD for pk in Placement.objects.filter(
        site_category=cat, **{f"{FIELD[w]}__isnull": False}).values_list(f"{FIELD[w]}_id", flat=True)}
    posts = [p for p in classify.all_posts(lambda qs: classify.with_classification(qs.filter(stage="post")))
             if (p.writer, p.pk) not in taken]
    posts.sort(key=lambda p: p.updated_at, reverse=True)
    posts.sort(key=classify.sort_key)
    posts.sort(key=lambda p: p.target != cat.blog.name)  # 이 사이트로 고른 글을 위에
    return [(f"{p.writer}:{p.pk}", f"{'[' + p.target + '] ' if p.target else ''}{p.title} — {classify.label_of(p)}") for p in posts]


def _top(skind, sobj):
    """오른쪽 위: 고른 사이트·사이트 카테고리의 매핑. 안 골랐으면 모든 매핑."""
    ctx = {"skind": skind, "sobj": sobj, "skind_label": KIND_LABEL.get(skind, "")}
    if sobj is None:
        ctx.update(placements=list(_placements_qs().order_by("site_category__blog__order", "site_category__order", "created_at")),
                   show_site=True, show_cat=True)
        return ctx
    cats = [sobj] if skind == "sitecat" else list(sobj.site_categories.all())
    if skind == "sitecat" and not sobj.parent_id:
        cats += list(sobj.children.all())
    ctx.update(placements=list(_placements_qs().filter(site_category__in=cats).order_by(
        "site_category__parent__order", "site_category__order", "created_at")), show_cat=len(cats) > 1)
    if skind == "sitecat":
        ctx.update(candidates=_candidates(sobj))
    return ctx


def index(request, form=None, form_sel=""):
    _nav(request)
    try:  # AI 가 남긴 분류 변경 파일(일일루틴/분류변경)을 먼저 반영한다
        from . import changes
        changes.sync()
    except Exception:
        pass
    g = request.GET
    site_sel, sel, w_raw = g.get("site", ""), g.get("sel", ""), g.get("w", "")
    if not site_sel and _is_site(sel):  # 예전 주소 ?sel=k7
        site_sel, sel = sel, ""
    skind, sobj = _find(site_sel)
    if skind not in SITE_KINDS or sobj is None:
        site_sel, skind, sobj = "", None, None
    ckind, cobj = _find(sel)
    if ckind not in CLASS_KINDS or cobj is None:
        sel, ckind, cobj = "", "all", None
    w = _writer(w_raw)
    today = g.get("today") == "1"
    site_names = sites.names()
    psite = g.get("psite", "")
    if psite != NO_SITE and psite not in site_names:
        psite = ""

    edit = form_sel or g.get("edit", "")
    if edit == "1":  # 예전 주소: 고른 것을 고친다
        edit = sel or site_sel
    top_form = bottom_form = None
    if edit and edit == site_sel and skind in EDITABLE:
        top_form = form if form_sel else FORMS[skind](instance=sobj)
    elif edit and edit == sel and ckind in EDITABLE:
        bottom_form = form if form_sel else FORMS[ckind](instance=cobj)

    here = _merge(request.get_full_path())
    ctx = {
        "page_title": "글 매핑 관리",
        "site_sel": site_sel, "sel": sel, "w": w, "kind": ckind,
        "site_q": f"site={site_sel}&" if site_sel else "",
        "class_q": urlencode({"sel": sel}) if sel else "",
        "here": here,
        "status_choices": Placement.Status.choices,
        "publish_choices": classify.post_model("tistory").Publish.choices,  # 아래 글 목록의 발행 칸
        # 아래(글 분류)
        "cobj": cobj, "ckind_label": {"all": "글 분류"}.get(ckind, KIND_LABEL.get(ckind, "")),
        "cpath": _path(ckind, cobj),
        "bottom_form": bottom_form,
        "posts": _posts(ckind, cobj, today, psite),
        "today": today, "psite": psite, "no_site": NO_SITE, "site_names": site_names,
        "today_url": "?" + urlencode({k: v for k, v in {"site": site_sel, "sel": sel, "today": "" if today else "1",
                                                          "psite": psite}.items() if v}),
        # 위(사이트 카테고리)
        "spath": _path(skind, sobj, w) if sobj else [],
        "top_form": top_form,
        **_top(skind, sobj),
    }
    partial = request.headers.get("X-Partial")
    if partial in ("top", "bottom"):
        return render(request, f"blog_types/_pane_{partial}.html", ctx)
    ctx.update({
        "tree": classify.class_tree(),
        "sites": _site_tree(),
        "open": _open_branches(ckind, cobj) | (_open_branches(skind, sobj) if sobj else set()),
    })
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
        return redirect(_merge(_next(request), obj.sel, w))
    request.GET = request.GET.copy()
    for key, value in parse_qsl(urlsplit(_next(request)).query):
        request.GET[key] = value
    if _is_site(obj.sel):  # 고치던 것이 그 칸에 골라져 있어야 오류와 함께 다시 보인다
        request.GET["site"] = obj.sel
    else:
        request.GET.update({"sel": obj.sel, "w": w})
    return index(request, form=form, form_sel=obj.sel)


@require_POST
def add(request, kind):
    """이름만으로 바로 추가하고, 추가한 것을 골라 둔다 (설명은 연필로 이어서 쓴다)."""
    name = " ".join(request.POST.get("name", "").split())
    parent_sel = request.POST.get("parent", "")
    w = _writer(request.POST.get("w", ""))
    nxt = _next(request)
    back = _merge(nxt, parent_sel, w)
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
    return redirect(_merge(nxt, obj.sel, w))


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
    return redirect(_merge(_next(request), obj.sel, _writer(request.POST.get("w", "")), edit=obj.sel))


def delete(request, kind, pk):
    _nav(request)
    if kind not in EDITABLE:
        raise Http404
    obj = get_object_or_404(MODELS[kind], pk=pk)
    _, parent = _parent(kind, obj)
    w = _writer(request.GET.get("w", "") or request.POST.get("w", ""))
    nxt = _next(request)
    if request.method == "POST":
        label = obj.name
        obj.delete()
        messages.success(request, f"{KIND_LABEL[kind]} '{label}'을(를) 삭제했습니다.")
        return redirect(_merge(nxt, parent.sel, w) if parent else _merge(nxt))
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
        "back": _merge(nxt, obj.sel, w), "next": nxt, "w": w,
    })


# ── 매핑: 사이트 카테고리 ← 글 ─────────────────────────────────────

def _back(request, fallback):
    return redirect(_next(request) or fallback)


@require_POST
def place_add(request):
    cat = get_object_or_404(SiteCategory, pk=request.POST.get("site_category") or 0)
    raw = request.POST.get("post", "")
    w, _, pk = raw.rpartition(":")  # 'tistory:3' · 'naver:5'. 숫자만 오면 사이트 플랫폼의 편집기 글 (예전 폼)
    w = w if w in FIELD else _site_writer(cat.blog)
    post = classify.post_model(w).objects.filter(pk=pk if pk.isdigit() else 0, stage="post").first()
    status = request.POST.get("status") or Placement.Status.UNSAVED
    back = _url(cat.sel)
    if post is None or status not in Placement.Status.values:
        messages.warning(request, "넣을 글을 고르세요.")
        return _back(request, back)
    field = FIELD[w]
    if Placement.objects.filter(site_category=cat, **{field: post}).exists():
        messages.warning(request, "이미 넣은 글입니다.")
        return _back(request, back)
    Placement.objects.create(site_category=cat, status=status, **{field: post})
    messages.success(request, f"'{post.title}'을(를) {cat.blog.name} › {cat}에 넣었습니다.")
    return _back(request, back)


@require_POST
def place_status(request, pk):
    """넣은 곳의 발행 상태 (미발행 · 발행 완료). 글의 발행 상태도 맞춘다 (sites.sync_post)."""
    placement = get_object_or_404(Placement, pk=pk)
    status = request.POST.get("value")
    if status in Placement.Status.values and status != placement.status:
        placement.status = status
        placement.save(update_fields=["status", "updated_at"])
        sites.sync_post(placement.post)
    return _back(request, _url(placement.site_category.sel))


@require_POST
def place_remove(request, pk):
    placement = get_object_or_404(Placement, pk=pk)
    sel = placement.site_category.sel
    placement.delete()
    messages.success(request, "사이트 카테고리에서 뺐습니다. 휴지통에서 7일 동안 되돌릴 수 있습니다.")
    return _back(request, _url(sel))
