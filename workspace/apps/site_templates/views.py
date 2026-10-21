"""사이트별 템플릿 화면.

- 메인 (2026-10-17 사용자): 왼쪽은 카테고리 관리처럼 사이트 › 카테고리 › 하위 카테고리 트리. 카테고리마다 컨셉이 있어서
  고르면 오른쪽 위에서 그 컨셉을 보고 고친다 (사이트를 고르면 사이트 컨셉 · 템플릿 고치기로). 오른쪽 아래는 변환할 글:
  발행예정글(발행 전) 중 미변환인 글. 카테고리 관리에서 고른 곳(사이트·카테고리)에 넣은 글만 '변환' 버튼이 뜨고,
  '변환 가능 글 전체 변환'은 그 범위의 미변환을 한꺼번에. 변환은 PC 터미널의 claude 가 한다 (run → jbroutine:convert 링크 →
  apps/routines/local_run.py). claude 는 변환본을 api_save 주소로 보낸다 (설정의 보고 토큰).
  그 아래는 변환 요청 · 완료 · 확인한 것 (누르면 변환 화면).
- 사이트: 컨셉·말투·구성·지킬 것과 플랫폼 붙여넣기 포맷 고치기에만 집중한다.
- 변환: 원문 ↔ 변환본. 변환 요청 → (Claude 가 변환본을 채움) → 변환 완료 → 확인 완료. 변환본은 그 사이트 에디터에 맞게 복사한다.
- requests.json: 변환 요청인 글의 요청문 (Claude 가 읽는다)
"""
import hmac
import re
from collections import Counter
from urllib.parse import parse_qsl, quote

import markdown
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.db.models import Prefetch
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.blog_rules.models import Blog
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


def index(request):
    """사이트별 템플릿 (2026-10-22 사용자): 변환은 글 관리로 옮기고, 여기서는 글쓰기·변환 컨셉과 규칙에 집중한다.
    왼쪽 트리에서 고른 것에 따라 오른쪽이 바뀐다 — 없음: 사이트마다 요약 / 사이트: 컨셉·템플릿·붙여넣기 포맷 고치기 +
    카테고리 컨셉 목록 / 카테고리: 그 카테고리 컨셉 고치기 + 같이 적용되는 사이트 컨셉·템플릿."""
    _nav(request)
    sel = request.GET.get("site", "")
    kind, obj = _pick(sel)
    if obj is None:
        sel = ""
    here = f"{reverse('site_templates:index')}?site={sel}" if sel else reverse("site_templates:index")
    concept_form = None
    if kind == "sitecat":
        concept_form = CategoryConceptForm(request.POST if request.method == "POST" else None, instance=obj, prefix="k")
        if request.method == "POST" and concept_form.is_valid():
            concept_form.save()
            messages.success(request, f"{obj.blog.name} › {obj} 컨셉을 저장했습니다.")
            return redirect(here)
    blog = obj if kind == "site" else (obj.blog if kind == "sitecat" else None)
    path = []
    if blog:
        path.append((blog.name, f"?site={blog.sel}"))
    if kind == "sitecat":
        if obj.parent_id:
            path.append((obj.parent.name, f"?site={obj.parent.sel}"))
        path.append((obj.name, f"?site={obj.sel}"))
    ctx = {"page_title": "사이트별 템플릿", "sites": _tree([]), "sel": sel, "kind": kind, "obj": obj, "blog": blog,
           "path": path, "here": here, "concept_form": concept_form}
    if blog:
        tpl, fmt = prompt.template_for(blog), prompt.format_for(blog.platform)
        ctx.update(tpl=tpl, fmt=fmt, cats=_cats_of(blog))
        if kind == "site":
            ctx.update(site_concept_form=ConceptForm(instance=blog, prefix="c"), tpl_form=TemplateForm(instance=tpl, prefix="t"),
                       fmt_form=FormatForm(instance=fmt, prefix="f"))
        else:
            ctx.update(parent_concept=obj.parent.concept if obj.parent_id else "",
                       kids=list(obj.children.all()) if not obj.parent_id else [])
    else:
        for b in ctx["sites"]:
            b.tpl = prompt.template_for(b)
            b.cats_all = _cats_of(b)
            b.cats_done = sum(1 for c in b.cats_all if c.concept.strip())
        ctx["requested"] = Placement.objects.filter(convert_status=Placement.Convert.REQUESTED).count()
    return render(request, "site_templates/index.html", ctx)


def _cats_of(blog):
    """그 사이트의 카테고리를 트리 순서대로 (하위는 .depth 1)"""
    out = []
    for c in SiteCategory.objects.filter(blog=blog, parent=None).prefetch_related("children").order_by("order", "pk"):
        c.depth = 0
        out.append(c)
        for k in c.children.all():
            k.depth = 1
            out.append(k)
    return out


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
    pls = [pl for pl in pls if pl.post is not None and pl.post.stage in ("review", "post")]  # 검토글도 (2026-10-22)
    if not pls:
        return JsonResponse({"error": "변환할 글이 없습니다. 카테고리 관리에서 카테고리에 먼저 넣으세요."}, status=400)
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
    """변환본 받기 (PC 터미널의 claude 가 curl 로 보낸다). 토큰이 맞아야 저장한다. title · body · tags · check(사실 점검 기록)."""
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
    if "check" in data:  # 사실 점검 기록 (고친 것 · 미정 · 확인한 출처)
        placement.converted_check = data["check"].replace("\r\n", "\n").strip()
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
        else:
            messages.warning(request, "저장하지 못했습니다. 칸을 확인하세요.")
    # 사이트 화면은 사이트별 템플릿 메인(그 사이트를 고른 오른쪽)으로 합쳤다 (2026-10-22)
    return redirect(f"{reverse('site_templates:index')}?site={blog.sel}")


def _render_for(placement, text):
    """그 사이트 플랫폼에 맞는 (미리보기 HTML, 서식 복사용 HTML, 글자만, 복사용 HTML).
    네이버는 네이버 글쓰기와, 티스토리·블로거는 티스토리 글쓰기와 같은 인라인 style HTML 을 쓴다.
    꾸밈 없는 HTML 을 붙이면 표 테두리·머리글 색이 빠지고 머리글 줄이 표 밖으로 빠진다 (2026-10-20 사용자).
    워드프레스만 꾸밈 없는 HTML (블록 에디터가 인라인 style 을 지운다)."""
    platform = placement.site_category.blog.platform
    if platform == Blog.Platform.NAVER:  # 미리보기도 붙여넣을 HTML 그대로 (문단 사이 빈 줄까지 네이버와 같게)
        from apps.naver_writing.render import needs_gaps, paste_html, plain_text, render_body
        html = render_body(text)
        rich = paste_html(html, gaps=needs_gaps(text, html))
        return rich, rich, plain_text(html), paste.clean_html(text)
    from apps.writing.render import plain_text, render_body
    html = paste.clean_html(text) if platform == Blog.Platform.WORDPRESS else render_body(text)
    return html, html, plain_text(html), html


def _tags_for(placement):
    """태그 칸에 붙일 꼴. 네이버는 '#태그 #태그' (쉼표로 붙이면 한 태그로 붙는다), 나머지는 쉼표 그대로."""
    if placement.site_category.blog.platform == Blog.Platform.NAVER:
        from apps.naver_writing.render import tag_line
        return tag_line(placement.converted_tags)
    return placement.converted_tags


class ConvertForm(_Styled):
    class Meta:
        model = Placement
        fields = ["convert_note", "converted_title", "converted_body", "converted_tags", "converted_check"]
        widgets = {"converted_body": forms.Textarea(attrs={"rows": 18, "spellcheck": "false"}),
                   "converted_check": forms.Textarea(attrs={"rows": 6, "spellcheck": "false"})}


_URL = re.compile(r'(?<![="\w>])(https?://[^\s<)]+)')


def _check_html(text):
    """사실 점검 기록(마크다운 목록) → HTML. 글은 이스케이프하고, 출처 주소는 누르면 열리게."""
    text = (text or "").strip()
    if not text:
        return ""
    html = markdown.markdown(escape(text), extensions=["sane_lists"])
    return _URL.sub(r'<a href="\1" target="_blank" rel="noopener">\1</a>', html)


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
            nxt = request.POST.get("next", "")  # 글 관리 펼침 칸에서 저장하면 그 목록으로
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect("site_templates:convert", pk=placement.pk)
        if request.headers.get("X-Requested-With") == "fetch":
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    return render(request, "site_templates/convert.html", {"page_title": "변환", **convert_context(placement, form)})


def convert_context(placement, form=None):
    """변환 화면 본문(_convert_body.html)에 넣을 것. 변환 화면과 글 관리 펼침 칸이 같이 쓴다."""
    post = placement.post
    from apps.writing.render import render_body
    conv_html, rich, plain, clean = (_render_for(placement, placement.converted_body) if placement.converted_body
                                     else ("", "", "", ""))
    naver = placement.site_category.blog.platform == Blog.Platform.NAVER
    return {
        "pl": placement, "blog": placement.site_category.blog, "post": post,
        "form": form or ConvertForm(instance=placement),
        "original_html": render_body(post.body), "converted_html": conv_html, "paste_html": rich, "plain_text": plain,
        "clean_html": clean, "paste": paste.for_platform(placement.site_category.blog.platform),
        "is_naver": naver, "tags_copy": _tags_for(placement),
        "tag_items": [t.lstrip("#") for t in _tags_for(placement).split()] if naver else [],
        "tag_bookmarklet": paste.naver_tag_bookmarklet(),
        "check_html": _check_html(placement.converted_check),
        "request_text": prompt.build(placement),
    }


def panel(request):
    """글 관리에서 글 줄을 누르면 그 아래에 펼치는 변환 칸 (2026-10-22 사용자: 사이트별 템플릿의 변환 화면을 글 관리로).
    ?p=tistory:3 [&pl=<매핑 번호>] [&next=<저장 뒤 돌아갈 주소>]. 넣은 곳이 없으면 원문만, 변환 전이면 변환본은 비어 있다."""
    from apps.blog_types.posts import _one
    post = _one(request.GET.get("p"))
    if post is None:
        return HttpResponse("글을 찾지 못했습니다.", status=404)
    pls = list(post.placements.select_related("site_category__blog", "site_category__parent"))
    pick = request.GET.get("pl", "")
    pl = next((x for x in pls if str(x.pk) == pick), pls[0] if pls else None)
    nxt = request.GET.get("next", "")
    ctx = convert_context(pl) if pl else {"post": post}
    if pl is None:
        from apps.writing.render import render_body
        ctx["original_html"] = render_body(post.body)
    ctx.update({"placements": pls, "next": nxt if nxt.startswith("/") and not nxt.startswith("//") else "",
                "panel_url": f"{reverse('site_templates:panel')}?p={request.GET.get('p')}&next={quote(nxt)}"})
    return render(request, "site_templates/_panel.html", ctx)


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
