"""사이트별 템플릿 화면.

- 메인 (2026-10-17 사용자): 왼쪽은 글 매핑 관리처럼 사이트 › 카테고리 › 하위 카테고리 트리. 카테고리마다 컨셉이 있어서
  고르면 오른쪽 위에서 그 컨셉을 보고 고친다 (사이트를 고르면 사이트 컨셉 · 템플릿 고치기로). 오른쪽 아래는 변환할 글:
  발행예정글(발행 전) 중 미변환인 글. 글 매핑 관리에서 고른 곳(사이트·카테고리)에 넣은 글만 '변환' 버튼이 뜨고,
  '변환 가능 글 전체 변환'은 그 범위의 미변환을 한꺼번에. 변환은 PC 터미널의 claude 가 한다 (run → jbroutine:convert 링크 →
  apps/routines/local_run.py). claude 는 변환본을 api_save 주소로 보낸다 (설정의 보고 토큰).
  그 아래는 변환 요청 · 완료 · 확인한 것 (누르면 변환 화면).
- 사이트: 컨셉·말투·구성·지킬 것과 플랫폼 붙여넣기 포맷 고치기에만 집중한다.
- 변환: 원문 ↔ 변환본. 변환 요청 → (Claude 가 변환본을 채움) → 변환 완료 → 확인 완료. 변환본은 그 사이트 에디터에 맞게 복사한다.
- requests.json: 변환 요청인 글의 요청문 (Claude 가 읽는다)
"""
import hmac
from collections import Counter
from urllib.parse import parse_qsl

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.db.models import Prefetch
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.blog_rules.models import Blog
from apps.blog_types import classify
from apps.blog_types.models import Placement, SiteCategory
from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting

from . import paste, prompt
from .models import PlatformFormat, SiteTemplate


class _Styled(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


class ConceptForm(_Styled):
    """사이트의 컨셉 한 줄 (운영 화면과 같은 값)"""
    class Meta:
        model = Blog
        fields = ["content"]
        labels = {"content": "컨셉"}


class TemplateForm(_Styled):
    class Meta:
        model = SiteTemplate
        fields = ["tone", "structure", "rules"]
        widgets = {name: forms.Textarea(attrs={"rows": 5}) for name in fields}


class FormatForm(_Styled):
    class Meta:
        model = PlatformFormat
        fields = ["guide"]
        widgets = {"guide": forms.Textarea(attrs={"rows": 8})}


def _nav(request):
    request.nav_key = "site_templates"


def _placements(blog=None):
    qs = Placement.objects.select_related("site_category__blog", "site_category__parent", "tistory_post", "naver_post")
    return qs.filter(site_category__blog=blog) if blog else qs


class CategoryConceptForm(_Styled):
    class Meta:
        model = SiteCategory
        fields = ["concept"]
        widgets = {"concept": forms.Textarea(attrs={"rows": 4})}


def _pick(sel):
    """?site= 값 → ('site', Blog) · ('sitecat', SiteCategory) · (None, None)"""
    kind = {"b": "site", "k": "sitecat"}.get((sel or "")[:1])
    pk = (sel or "")[1:]
    if not kind or not pk.isdigit():
        return None, None
    obj = (Blog if kind == "site" else SiteCategory).objects.filter(pk=pk).first()
    return (kind, obj) if obj else (None, None)


def _scope(kind, obj):
    """고른 것 아래의 사이트 카테고리 pk (None = 모두)"""
    if kind == "site":
        return set(SiteCategory.objects.filter(blog=obj).values_list("pk", flat=True))
    if kind == "sitecat":
        return {obj.pk, *obj.children.values_list("pk", flat=True)}
    return None


def _tree(todo_cats):
    """왼쪽 트리: 사이트 › 카테고리 › 하위. 숫자는 그 아래 변환할 수 있는 글(미변환 매핑) 수."""
    counts = Counter(todo_cats)
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


def _todo_posts(scope):
    """변환할 글: 발행예정글 · 발행 전 · 미변환 (넣은 곳이 없거나, 넣은 곳 중 미변환이 있는 글).
    글마다 .ready = 고른 범위 안의 미변환 매핑 (변환 버튼). 버튼이 있는 글을 위로."""
    none = Placement.Convert.NONE

    def narrow(qs):
        qs = qs.filter(stage="post").exclude(publish_status=qs.model.Publish.DONE)
        return classify.with_classification(qs).prefetch_related(Prefetch("placements", queryset=_placements()))
    out = []
    for p in classify.all_posts(narrow):
        pls = list(p.placements.all())
        if pls and all(pl.convert_status != none for pl in pls):
            continue
        p.cls_label = classify.label_of(p)
        p.todo = [pl for pl in pls if pl.convert_status == none]
        p.ready = [pl for pl in p.todo if scope is None or pl.site_category_id in scope]
        out.append(p)
    out.sort(key=lambda p: p.updated_at, reverse=True)
    out.sort(key=lambda p: not p.ready)
    return out


def index(request):
    _nav(request)
    sel = request.GET.get("site", "")
    kind, obj = _pick(sel)
    if obj is None:
        sel = ""
    scope = _scope(kind, obj)
    concept_form = None
    if kind == "sitecat":
        concept_form = CategoryConceptForm(request.POST if request.method == "POST" else None, instance=obj, prefix="k")
        if request.method == "POST" and concept_form.is_valid():
            concept_form.save()
            messages.success(request, f"{obj.blog.name} › {obj} 컨셉을 저장했습니다.")
            return redirect(f"{reverse('site_templates:index')}?site={sel}")
    posts = _todo_posts(scope)
    ready = [pl.pk for p in posts for pl in p.ready]
    done = _placements().exclude(convert_status=Placement.Convert.NONE).order_by("-updated_at")
    if scope is not None:
        done = done.filter(site_category__in=scope)
    todo_cats = [pl.site_category_id for p in posts for pl in p.todo]
    blog = obj if kind == "site" else (obj.blog if kind == "sitecat" else None)
    path = []
    if blog:
        path.append((blog.name, f"?site={blog.sel}"))
    if kind == "sitecat":
        if obj.parent_id:
            path.append((obj.parent.name, f"?site={obj.parent.sel}"))
        path.append((obj.name, f"?site={obj.sel}"))
    return render(request, "site_templates/index.html", {
        "page_title": "사이트별 템플릿", "sites": _tree(todo_cats), "sel": sel, "kind": kind, "obj": obj, "blog": blog,
        "path": path, "concept_form": concept_form, "parent_concept": obj.parent.concept if kind == "sitecat" and obj.parent_id else "",
        "posts": posts, "ready_ids": ",".join(map(str, ready)), "ready_count": len(ready),
        "done": list(done[:100]), "has_token": bool(AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)),
        "requested": Placement.objects.filter(convert_status=Placement.Convert.REQUESTED).count(),
    })


@require_POST
def run(request):
    """'변환'·'전체 변환': 고른 매핑을 변환 요청으로 바꾸고, PC 터미널 claude 에게 줄 안내문을 돌려준다 (JSON).
    화면이 안내문을 복사하고 jbroutine:convert 링크로 터미널을 연다. 변환본은 claude 가 api_save 로 보낸다."""
    token = AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)
    if not token:
        return JsonResponse({"error": "설정 화면에서 보고 토큰을 먼저 만드세요. claude 가 변환본을 서버로 보낼 때 씁니다."}, status=400)
    ids = [int(x) for x in request.POST.get("ids", "").split(",") if x.strip().isdigit()]
    pls = list(_placements().filter(pk__in=ids, convert_status__in=[Placement.Convert.NONE, Placement.Convert.REQUESTED])
               .order_by("site_category__blog__order", "pk"))
    pls = [pl for pl in pls if pl.post is not None and pl.post.stage == "post"]
    if not pls:
        return JsonResponse({"error": "변환할 글이 없습니다. 글 매핑 관리에서 카테고리에 먼저 넣으세요."}, status=400)
    for pl in pls:
        pl.convert_status = Placement.Convert.REQUESTED
        pl.save(update_fields=["convert_status", "updated_at"])
    now = timezone.localtime()
    return JsonResponse({"prompt": prompt.launcher(request, pls, token), "key": f"cv-{now:%H%M%S}",
                         "day": now.date().isoformat(), "count": len(pls)})


def _form_fields(request):
    """변환본 보내기의 title · body · tags. 칸마다 따로 글자를 맞춘다 (2026-10-20: 제목·태그가 깨졌다).
    Windows 의 curl 은 명령줄에 쓴 한글(title=… · tags=…)을 cp949 로 보내고, 파일(body@…)은 UTF-8 그대로 보낸다.
    Django 는 한 요청을 한 글자셋(UTF-8)으로 읽으므로 cp949 칸이 깨진다 → 칸마다 UTF-8 로 안 읽히면 cp949 로 읽는다."""
    if request.content_type != "application/x-www-form-urlencoded":
        return request.POST
    out = {}
    for key, value in parse_qsl(request.body.decode("ascii", "replace"), keep_blank_values=True, encoding="latin-1"):
        raw = value.encode("latin-1")  # 퍼센트 풀기만 한 바이트
        for encoding in ("utf-8", "cp949"):
            try:
                out[key] = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            out[key] = raw.decode("utf-8", "replace")
    return out


@csrf_exempt
@login_not_required
@require_POST
def api_save(request, pk):
    """변환본 받기 (PC 터미널의 claude 가 curl 로 보낸다). 토큰이 맞아야 저장한다. title · body · tags."""
    token = AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)
    if not token or not hmac.compare_digest(request.GET.get("token", ""), token):
        return HttpResponseForbidden("token")
    placement = get_object_or_404(Placement, pk=pk)
    data = _form_fields(request)
    body = data.get("body", "").replace("\r\n", "\n").strip()
    if not body:
        return HttpResponseBadRequest("body 가 비었습니다")
    placement.converted_title = data.get("title", "").strip()[:200]
    placement.converted_tags = data.get("tags", "").strip()[:500]
    placement.converted_body = body
    placement.convert_status = Placement.Convert.DONE
    placement.converted_at = timezone.now()
    placement.save()
    return HttpResponse(f"ok {placement.pk} done", content_type="text/plain; charset=utf-8")


def site(request, pk):
    _nav(request)
    blog = get_object_or_404(Blog, pk=pk)
    tpl, fmt = prompt.template_for(blog), prompt.format_for(blog.platform)
    part = request.POST.get("part")
    concept_form = ConceptForm(request.POST if part == "template" else None, instance=blog, prefix="c")
    tpl_form = TemplateForm(request.POST if part == "template" else None, instance=tpl, prefix="t")
    fmt_form = FormatForm(request.POST if part == "format" else None, instance=fmt, prefix="f")
    if request.method == "POST":
        forms_ = [concept_form, tpl_form] if part == "template" else [fmt_form]
        if all(f.is_valid() for f in forms_):
            for f in forms_:
                f.save()
            messages.success(request, "저장했습니다.")
            return redirect("site_templates:site", pk=blog.pk)
    cv = Counter(_placements(blog).values_list("convert_status", flat=True))
    return render(request, "site_templates/site.html", {
        "page_title": f"{blog.name} 템플릿", "blog": blog, "concept_form": concept_form, "tpl_form": tpl_form,
        "fmt_form": fmt_form, "cv": {k: cv[k] for k in Placement.Convert.values},
    })


def _render_for(placement, text):
    """그 사이트 플랫폼에 맞는 (미리보기 HTML, 서식 복사용 HTML, 글자만, 깨끗한 HTML).
    네이버만 인라인 style 을 단 서식 HTML 을 쓴다. 나머지는 꾸밈 없는 HTML (포스팅자동화/13 문서)."""
    if placement.site_category.blog.platform == Blog.Platform.NAVER:
        from apps.naver_writing.render import paste_html, plain_text, render_body
        html = render_body(text)
        return html, paste_html(html), plain_text(html), paste.clean_html(text)
    from apps.writing.render import plain_text
    clean = paste.clean_html(text)
    return clean, clean, plain_text(clean), clean


class ConvertForm(_Styled):
    class Meta:
        model = Placement
        fields = ["convert_note", "converted_title", "converted_body", "converted_tags"]
        widgets = {"converted_body": forms.Textarea(attrs={"rows": 18, "spellcheck": "false"})}


def convert(request, pk):
    _nav(request)
    placement = get_object_or_404(Placement.objects.select_related("site_category__blog"), pk=pk)
    form = ConvertForm(request.POST or None, instance=placement)
    if request.method == "POST":
        action = request.POST.get("action", "save")
        if form.is_valid():
            placement = form.save(commit=False)
            if action == "request":
                placement.convert_status = Placement.Convert.REQUESTED
                messages.success(request, "변환을 요청했습니다. Claude 에게 '변환 요청 처리해줘'라고 하면 변환본을 채웁니다.")
            elif action == "check":
                placement.convert_status = Placement.Convert.CHECKED
                messages.success(request, "확인 완료로 바꿨습니다.")
            elif action == "reset":
                placement.convert_status = Placement.Convert.NONE
                messages.success(request, "미변환으로 되돌렸습니다.")
            elif placement.converted_body.strip():
                placement.convert_status = Placement.Convert.DONE
                placement.converted_at = timezone.now()
                messages.success(request, "변환본을 저장했습니다.")
            else:
                messages.success(request, "저장했습니다.")
            placement.save()
            if request.headers.get("X-Requested-With") == "fetch":
                return JsonResponse({"ok": True, "status": placement.convert_status})
            return redirect("site_templates:convert", pk=placement.pk)
        if request.headers.get("X-Requested-With") == "fetch":
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    post = placement.post
    from apps.writing.render import render_body
    original_html = render_body(post.body)
    conv_html, rich, plain, clean = (_render_for(placement, placement.converted_body) if placement.converted_body
                                     else ("", "", "", ""))
    return render(request, "site_templates/convert.html", {
        "page_title": "변환", "pl": placement, "blog": placement.site_category.blog, "post": post, "form": form,
        "original_html": original_html, "converted_html": conv_html, "paste_html": rich, "plain_text": plain,
        "clean_html": clean, "paste": paste.for_platform(placement.site_category.blog.platform),
        "request_text": prompt.build(placement),
    })


def requests_json(request):
    """변환 요청인 글: Claude 가 읽고 변환본을 채운다 (convert 주소에 action=save 로 보낸다)."""
    items = []
    for pl in _placements().filter(convert_status=Placement.Convert.REQUESTED).order_by("updated_at"):
        items.append({
            "id": pl.pk, "site": pl.site_category.blog.name, "platform": pl.site_category.blog.platform,
            "category": str(pl.site_category), "title": pl.post.title,
            "save_url": reverse("site_templates:convert", args=[pl.pk]), "prompt": prompt.build(pl),
        })
    return JsonResponse({"count": len(items), "items": items}, json_dumps_params={"ensure_ascii": False})


@require_POST
def quick_status(request, pk):
    placement = get_object_or_404(Placement, pk=pk)
    value = request.POST.get("value")
    if value in Placement.Convert.values:
        placement.convert_status = value
        placement.save(update_fields=["convert_status", "updated_at"])
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else reverse("site_templates:index"))
