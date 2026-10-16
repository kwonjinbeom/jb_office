"""사이트별 템플릿 화면.

- 메인 (2026-10-16 사용자): 포스트 관리 단계이면서 아직 발행 완료가 아닌 글 목록. 글마다 사이트(카테고리)를 골라 변환을 요청하고,
  이미 넣은 곳의 변환 상태를 본다. 위에는 사이트 카드(누르면 그 사이트의 컨셉·템플릿 고치기).
- 사이트: 컨셉·말투·구성·지킬 것과 플랫폼 붙여넣기 포맷 고치기에만 집중한다.
- 변환: 원문 ↔ 변환본. 변환 요청 → (Claude 가 변환본을 채움) → 변환 완료 → 확인 완료. 변환본은 그 사이트 에디터에 맞게 복사한다.
- requests.json: 변환 요청인 글의 요청문 (Claude 가 읽는다)
"""
from collections import Counter

from django import forms
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog_rules.models import Blog
from apps.blog_types import classify
from apps.blog_types.models import Placement, SiteCategory

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


def _first_line(text):
    return next((line.strip() for line in (text or "").splitlines() if line.strip()), "")


def _placements(blog=None):
    qs = Placement.objects.select_related("site_category__blog", "site_category__parent", "tistory_post", "naver_post")
    return qs.filter(site_category__blog=blog) if blog else qs


def _site_choices(sites):
    """사이트 골라 변환: 사이트마다 묶은 사이트 카테고리. 카테고리가 없는 사이트는 고를 수 없다 (글 매핑 관리에서 먼저 추가)."""
    groups = []
    cats = SiteCategory.objects.filter(parent=None).prefetch_related("children").order_by("order", "pk")
    by_blog = {}
    for c in cats:
        by_blog.setdefault(c.blog_id, []).append(c)
    for b in sites:
        rows = []
        for c in by_blog.get(b.pk, []):
            rows.append((c.pk, f"{b.name} › {c.name}"))
            rows += [(k.pk, f"{b.name} › {c.name} › {k.name}") for k in c.children.all()]
        groups.append({"blog": b, "rows": rows})
    return groups


def index(request):
    _nav(request)
    counts = Counter(Placement.objects.values_list("site_category__blog_id", "convert_status"))
    sites = list(Blog.objects.all())
    for b in sites:
        b.cv = {key: counts[(b.pk, key)] for key in Placement.Convert.values}
    from django.db.models import Prefetch
    pl_qs = _placements()

    def narrow(qs):
        qs = qs.filter(stage="post").exclude(publish_status=qs.model.Publish.DONE)
        return classify.with_classification(qs).prefetch_related(Prefetch("placements", queryset=pl_qs))
    posts = classify.all_posts(narrow)
    posts.sort(key=lambda p: p.updated_at, reverse=True)
    for p in posts:
        p.cls_label = classify.label_of(p)
    return render(request, "site_templates/index.html", {
        "page_title": "사이트별 템플릿", "sites": sites, "posts": posts, "site_choices": _site_choices(sites),
        "requested": sum(b.cv["requested"] for b in sites),
    })


@require_POST
def request_convert(request):
    """메인에서: 글 하나를 사이트 카테고리에 넣고(없으면) 변환을 요청한다."""
    cat = get_object_or_404(SiteCategory, pk=request.POST.get("site_category") or 0)
    writer, _, pk = request.POST.get("post", "").rpartition(":")
    if writer not in classify.WRITERS or not pk.isdigit():
        messages.warning(request, "글을 고르세요.")
        return redirect("site_templates:index")
    post = get_object_or_404(classify.post_model(writer), pk=pk, stage="post")
    field = "naver_post" if writer == "naver" else "tistory_post"
    placement, created = Placement.objects.get_or_create(site_category=cat, **{field: post})
    placement.convert_status = Placement.Convert.REQUESTED
    placement.save(update_fields=["convert_status", "updated_at"])
    messages.success(request, f"'{post.title}' → {cat.blog.name} › {cat} 변환을 요청했습니다. "
                              "Claude 에게 '변환 요청 처리해줘'라고 하면 변환본을 채웁니다.")
    return redirect("site_templates:index")


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
