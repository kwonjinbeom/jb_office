"""사이트별 템플릿 · 변환.

- 사이트별 템플릿 (index, 2026-10-22 사용자): 왼쪽 사이트 › 카테고리 › 하위 트리, 오른쪽은 글쓰기·변환 컨셉과 규칙을 보여 주기만 한다.
  고치기는 화면에서 하지 않고 사용자가 Claude 에게 따로 부탁한다.
- 변환은 글 관리(검토글·발행예정글)에서 한다: run · reconvert → jbroutine:convert 링크 → PC 터미널 claude
  (apps/routines/local_run.py). claude 는 변환본을 api_save 주소로 보낸다 (설정의 보고 토큰).
- 변환 화면 (convert · post_page · panel): 원문 ↔ 변환본 · 사실 점검 · 붙여넣기 HTML. 변환본은 그 사이트 에디터에 맞게 복사한다.
- requests.json: 변환 요청인 글의 요청문 (Claude 가 읽는다)
"""
import hmac
import re
from urllib.parse import parse_qsl, quote

import markdown
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.db.models import Prefetch
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.blog_rules.models import Blog
from apps.blog_types.models import Placement, SiteCategory
from apps.core import briefs
from apps.core.context_processors import _asset_version
from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting

from . import design, looks, paste, prompt

BRIEF_KEY = "convert_brief"  # 마지막 변환·재변환 안내문 (apps/core/briefs)


class _Styled(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


def _nav(request):
    request.nav_key = "site_templates"


def _placements(blog=None):
    qs = Placement.objects.select_related("site_category__blog", "site_category__parent", "tistory_post", "naver_post")
    return qs.filter(site_category__blog=blog) if blog else qs


def _pick(sel):
    """?site= 값 → ('site', Blog) · ('sitecat', SiteCategory) · (None, None)"""
    kind = {"b": "site", "k": "sitecat"}.get((sel or "")[:1])
    pk = (sel or "")[1:]
    if not kind or not pk.isdigit():
        return None, None
    obj = (Blog if kind == "site" else SiteCategory).objects.filter(pk=pk).first()
    return (kind, obj) if obj else (None, None)


def _tree():
    """왼쪽 트리: 사이트 › 카테고리 › 하위"""
    top = SiteCategory.objects.filter(parent=None).prefetch_related("children")
    return list(Blog.objects.prefetch_related(Prefetch("site_categories", queryset=top, to_attr="top_cats")))


def index(request):
    """사이트별 템플릿 (2026-10-22 사용자): 변환은 글 관리로 옮기고, 여기서는 글쓰기·변환 컨셉과 규칙을 보여 주기만 한다
    (고치기는 화면에서 하지 않고 사용자가 Claude 에게 따로 부탁한다). 왼쪽 트리에서 고른 것에 따라 —
    없음: 사이트마다 요약 / 사이트: 컨셉·템플릿·붙여넣기 포맷 + 카테고리 컨셉 목록 / 카테고리: 그 컨셉 + 같이 적용되는 것."""
    _nav(request)
    sel = request.GET.get("site", "")
    kind, obj = _pick(sel)
    if obj is None:
        sel = ""
    blog = obj if kind == "site" else (obj.blog if kind == "sitecat" else None)
    path = []
    if blog:
        path.append((blog.name, f"?site={blog.sel}"))
    if kind == "sitecat":
        if obj.parent_id:
            path.append((obj.parent.name, f"?site={obj.parent.sel}"))
        path.append((obj.name, f"?site={obj.sel}"))
    ctx = {"page_title": "사이트별 템플릿", "sites": _tree(), "sel": sel, "kind": kind, "obj": obj, "blog": blog,
           "path": path}
    if blog:
        tpl, fmt = prompt.template_for(blog), prompt.format_for(blog.platform)
        ctx.update(tpl=tpl, fmt=fmt, cats=_cats_of(blog))
        if kind == "sitecat":
            ctx.update(parent_concept=obj.parent.concept if obj.parent_id else "",
                       kids=list(obj.children.all()) if not obj.parent_id else [], **_design(obj, request))
    else:
        for b in ctx["sites"]:
            b.tpl = prompt.template_for(b)
            b.cats_all = _cats_of(b)
            b.cats_done = sum(1 for c in b.cats_all if c.concept.strip())
        ctx["requested"] = Placement.objects.filter(convert_status=Placement.Convert.REQUESTED).count()
    return render(request, "site_templates/index.html", ctx)


def _design(cat, request=None):
    """카테고리 › 디자인 컨셉 (2026-10-28 사용자): 요소마다 견본 마크다운을 변환과 같은 코드로 그린 iframe 문서.
    감싸는 class 는 변환 화면 미리보기와 같다 (네이버 st-naver · 티스토리·블로거 st-flat)."""
    platform, look = cat.blog.platform, _look(cat)
    wrap = {Blog.Platform.NAVER: " st-naver", Blog.Platform.TISTORY: " st-flat", Blog.Platform.BLOGGER: " st-flat"}.get(platform, "")
    head = (f'<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="{static("css/app.css")}?v={_asset_version()}">'
            '<body style="height:auto;margin:0;padding:14px 16px;background:#fff;zoom:.8">'  # 칸이 좁아 0.8 배로 (본문 폭 그대로 보이게)
            f'<div class="wr-article st-converted{wrap}">')
    out = []
    photos = {k: request.build_absolute_uri(static(v)) if request else static(v) for k, v in design.PHOTOS.items()}
    for it in design.items(platform, look, _heading_bar(cat), photos):
        it["doc"] = head + _render_cat(cat, it["md"])[0] + "</div></body>"
        out.append(it)
    looks_ = dict(SiteCategory._meta.get_field("look").choices)
    return {"design": out, "design_look": looks_.get(look, look)}


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
    return _launch(prompt.launcher(request, pls, token), "cv", len(pls))


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


@require_POST
def reconvert(request):
    """재변환 (2026-10-22 사용자): 글 관리에서 체크한 글 하나 + 코멘트. 변환 완료·확인 완료여도 다시 변환 요청으로 바꾸고,
    지난 변환본을 코멘트대로 고치는 안내문을 돌려준다 (JSON, 화면이 PC 터미널 claude 를 연다). ?p=tistory:3 · note."""
    from apps.blog_types.posts import _one
    token = AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)
    if not token:
        return JsonResponse({"error": "설정 화면에서 보고 토큰을 먼저 만드세요. claude 가 변환본을 서버로 보낼 때 씁니다."}, status=400)
    note = request.POST.get("note", "").strip()[:2000]
    if not note:
        return JsonResponse({"error": "무엇을 고칠지 코멘트를 적으세요."}, status=400)
    post = _one(request.POST.get("p"))
    if post is None:
        return JsonResponse({"error": "글을 찾지 못했습니다."}, status=400)
    pls = list(_placements().filter(**{"naver_post" if post._meta.app_label == "naver_writing" else "tistory_post": post}))
    if not pls:
        return JsonResponse({"error": "카테고리에 먼저 넣어야 변환할 수 있어요."}, status=400)
    for pl in pls:
        pl.convert_status = Placement.Convert.REQUESTED
        pl.save(update_fields=["convert_status", "updated_at"])
    return _launch(prompt.launcher(request, pls, token, redo=note), "rc", len(pls))


def _launch(text, prefix, count):
    """변환 안내문 JSON. 서버에도 잠깐 둔다 (2026-10-28 사용자: 전체 변환에서 '안내문을 복사하지 못했습니다' —
    안내문을 만드는 사이 브라우저가 복사를 거절했다). 복사가 막혀도 PC 가 링크의 key 로 brief 에서 받아 간다."""
    return JsonResponse({"prompt": text, "key": briefs.keep(BRIEF_KEY, prefix, text),
                         "day": timezone.localdate().isoformat(), "count": count})


@login_not_required
def brief(request, key):
    """PC 실행기(routines/local_run)가 클립보드에서 변환 안내문을 못 찾았을 때 받아 간다. 30분 안에 한 번만."""
    text = briefs.take(BRIEF_KEY, key)
    if text is None:
        return HttpResponse("안내문 없음 (30분이 지났거나 다시 눌렀습니다)", status=404)
    return HttpResponse(text, content_type="text/plain; charset=utf-8")


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
    body = paste.unwrap_images(data.get("body", "").replace("\r\n", "\n")).strip()
    if not body:
        return HttpResponseBadRequest("body 가 비었습니다")
    before = (placement.converted_title, placement.converted_body)
    if "title" in data:  # 안 보낸 칸은 그대로 둔다 (본문만 다시 보낼 때)
        placement.converted_title = data["title"].strip()[:200]
    if "tags" in data:
        placement.converted_tags = data["tags"].strip()[:500]
    if "check" in data:  # 사실 점검 기록 (고친 것 · 미정 · 확인한 출처)
        placement.converted_check = data["check"].replace("\r\n", "\n").strip()
    if "slug" in data:  # 워드프레스 글 주소 (2026-10-26)
        from . import wp_looks
        placement.converted_slug = wp_looks.clean_slug(data["slug"])[:120]
    placement.converted_body = body
    placement.convert_status = Placement.Convert.DONE
    placement.converted_at = timezone.now()
    extra = data.get("change", "").strip()  # 무엇을 고쳤는지 한 줄 (보내는 쪽이 적는다, 예: '맨 앞 한 문장 추가')
    if placement.status == Placement.Status.PUBLISHED and before[1] and (extra or before != (placement.converted_title, placement.converted_body)):
        # 발행한 글의 변환본이 바뀜 → 게시글 관리 '수정됨' + 변환글 보기 맨 위 한 줄 (2026-10-26 사용자)
        from apps.blog_types import sites
        lit = placement.changed_at is not None  # 이미 켜져 있으면 처음 제목·본문 변경을 이어 간다
        old_title = (sites.changed_old_title(placement.changed_note) if lit else None) or before[0]
        body_changed = before[1] != placement.converted_body or (lit and not placement.changed_note.startswith("제목만"))
        placement.changed_at = placement.converted_at
        placement.changed_note = sites.change_note(old_title, placement.converted_title, body_changed, extra)
    placement.save()
    return HttpResponse(f"ok {placement.pk} done", content_type="text/plain; charset=utf-8")


@csrf_exempt
@login_not_required
def api_wp(request, pk):
    """워드프레스 초안 재료 (2026-10-26 사용자: 변환이 끝나면 PC claude 가 REST API 로 초안을 올린다).
    서버(PythonAnywhere 무료)는 jinbaam.com 에 닿지 않아, PC 의 wp_draft 명령이 이 주소에서 재료를 받아 워드프레스에 올리고
    올린 글 번호를 POST 로 돌려준다 (다시 변환하면 같은 초안을 고친다). 토큰은 api_save 와 같다."""
    token = AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)
    if not token or not hmac.compare_digest(request.GET.get("token", ""), token):
        return HttpResponseForbidden("token")
    placement = get_object_or_404(Placement.objects.select_related("site_category__blog", "site_category__parent"), pk=pk)
    if placement.site_category.blog.platform != Blog.Platform.WORDPRESS:
        return HttpResponseBadRequest("워드프레스 글이 아닙니다")
    if request.method == "POST":
        try:
            placement.wp_post_id = int(request.POST.get("wp_post_id", ""))
        except ValueError:
            return HttpResponseBadRequest("wp_post_id")
        placement.save(update_fields=["wp_post_id", "updated_at"])
        return HttpResponse(f"ok {placement.pk} wp {placement.wp_post_id}", content_type="text/plain; charset=utf-8")
    if not placement.converted_body.strip():
        return HttpResponseBadRequest("변환본이 없습니다")
    from . import wp_looks
    title = placement.converted_title or placement.post.title
    return JsonResponse({
        "id": placement.pk, "title": title,
        "content": wp_looks.paste_html(placement.converted_body, _look(placement.site_category)),
        "category": placement.site_category.name,
        "tags": [t.strip() for t in placement.converted_tags.split(",") if t.strip()],
        "slug": placement.converted_slug or wp_looks.auto_slug(title),
        "excerpt": wp_looks.excerpt(placement.converted_body),
        "hero": _hero(placement.converted_body),
        "wp_post_id": placement.wp_post_id,
    }, json_dumps_params={"ensure_ascii": False})


@login_not_required
def api_state(request):
    """PC 터미널 claude 가 서버 값을 읽는 곳 (2026-10-23: 발행한 글의 변환본을 고쳐 다시 보내려면 매핑 번호·지난 변환본이 필요하다).
    토큰은 api_save 와 같다. ?site=<사이트 이름> 이면 그 사이트만. 사이트 템플릿 · 카테고리 컨셉 · 넣은 글(원문과 변환본)."""
    token = AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)
    if not token or not hmac.compare_digest(request.GET.get("token", ""), token):
        return HttpResponseForbidden("token")
    blogs = Blog.objects.all()
    if request.GET.get("site"):
        blogs = blogs.filter(name=request.GET["site"])
    out = []
    for blog in blogs:
        tpl = prompt.template_for(blog)
        cats = [{"id": c.pk, "name": str(c), "concept": c.concept} for c in _cats_of(blog)]
        pls = []
        for pl in _placements(blog):
            post = pl.post
            if post is None:
                continue
            pls.append({"id": pl.pk, "category": str(pl.site_category), "status": pl.status,
                        "convert": pl.convert_status, "title": post.title, "body": post.body,
                        "converted_title": pl.converted_title, "converted_tags": pl.converted_tags,
                        "converted_body": pl.converted_body, "converted_check": pl.converted_check})
        out.append({"name": blog.name, "platform": blog.platform, "content": blog.content,
                    "template": {"tone": tpl.tone, "structure": tpl.structure, "rules": tpl.rules},
                    "categories": cats, "placements": pls})
    return JsonResponse({"sites": out}, json_dumps_params={"ensure_ascii": False})


def _token_ok(request):
    token = AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)
    return bool(token) and hmac.compare_digest(request.GET.get("token", ""), token)


@login_not_required
def api_posts(request):
    """클라우드 claude 가 글 관리의 글을 읽는 곳 (2026-10-25 사용자: 클라우드 세션에서 오늘 쓴 글과 임시글을 변환).
    토큰은 api_save 와 같다. 먼저 새 원고를 임시글으로 가져오고(auto_import_drafts), 임시글·검토글·발행예정글을 넣은 곳과 함께."""
    if not _token_ok(request):
        return HttpResponseForbidden("token")
    from apps.blog_types import classify
    from apps.writing.views import auto_import_drafts
    added = auto_import_drafts()
    out = []
    for w in classify.WRITERS:
        model = classify.post_model(w)
        for post in model.objects.filter(stage__in=["temp", "review", "post"]).order_by("-created_at"):
            out.append({"ref": f"{w}:{post.pk}", "title": post.title, "stage": post.stage, "target": post.target,
                        "created": timezone.localtime(post.created_at).isoformat(timespec="minutes"),
                        "placements": [{"id": pl.pk, "site_category": pl.site_category_id, "category": f"{pl.site_category.blog.name} › {pl.site_category}",
                                        "convert": pl.convert_status, "status": pl.status}
                                       for pl in post.placements.select_related("site_category__blog")]})
    return JsonResponse({"imported": added, "posts": out}, json_dumps_params={"ensure_ascii": False})


@csrf_exempt
@login_not_required
@require_POST
def api_place(request):
    """클라우드 claude 가 글을 사이트 카테고리에 넣고 변환을 요청하는 곳: post=tistory:3 · site_category=<번호>.
    변환은 검토글·발행예정글만 되므로 임시글이면 검토글로 옮긴다. 이미 넣은 곳이면 그대로 쓴다.
    돌려주는 것: 넣은 곳 번호와 변환 안내문 (PC 의 '변환'과 같은 prompt.launcher — 변환본은 api_save 로 보낸다)."""
    if not _token_ok(request):
        return HttpResponseForbidden("token")
    from apps.blog_types import classify
    cat = get_object_or_404(SiteCategory, pk=request.POST.get("site_category") or 0)
    w, _, pk = request.POST.get("post", "").rpartition(":")
    if w not in classify.WRITERS or not pk.isdigit():
        return HttpResponseBadRequest("post=tistory:3 꼴")
    post = get_object_or_404(classify.post_model(w), pk=pk, stage__in=["temp", "review", "post"])
    if post.stage == "temp":
        post.stage = "review"
        post.save(update_fields=["stage", "updated_at"])
    field = "naver_post" if w == "naver" else "tistory_post"
    pl, created = Placement.objects.get_or_create(site_category=cat, **{field: post})
    if pl.convert_status in (Placement.Convert.NONE, Placement.Convert.REQUESTED):
        pl.convert_status = Placement.Convert.REQUESTED
        pl.save(update_fields=["convert_status", "updated_at"])
    return JsonResponse({"id": pl.pk, "created": created, "stage": post.stage, "convert": pl.convert_status,
                         "prompt": prompt.launcher(request, [pl], AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY))},
                        json_dumps_params={"ensure_ascii": False})


@csrf_exempt
@login_not_required
@require_POST
def api_stage(request):
    """클라우드 claude 가 글의 단계를 이웃 단계로 옮기는 곳: post=tistory:3 · to=review|post|temp (2026-10-25 사용자: 변환한 글을 발행예정글로).
    글 관리의 체크한 글 옮기기(posts.bulk)와 같은 규칙 — 이웃 단계로만 (임시 → 발행예정은 바로), 발행 완료한 글은 되돌리지 않는다."""
    if not _token_ok(request):
        return HttpResponseForbidden("token")
    from apps.blog_types import classify
    w, _, pk = request.POST.get("post", "").rpartition(":")
    if w not in classify.WRITERS or not pk.isdigit():
        return HttpResponseBadRequest("post=tistory:3 꼴")
    post = get_object_or_404(classify.post_model(w), pk=pk)
    to = request.POST.get("to", "")
    if post.stage != to:
        if not post.can_move_to(to):
            return JsonResponse({"error": f"{post.stage} → {to} 로는 옮길 수 없습니다"}, status=400)
        post.stage = to
        post.save(update_fields=["stage", "updated_at"])
    return JsonResponse({"post": f"{w}:{post.pk}", "stage": post.stage})


def site(request, pk):
    """예전 사이트 화면 주소 → 사이트별 템플릿에서 그 사이트를 고른 화면 (2026-10-22: 화면에서는 보기만)."""
    blog = get_object_or_404(Blog, pk=pk)
    return redirect(f"{reverse('site_templates:index')}?site={blog.sel}")


def _render_for(placement, text):
    return _render_cat(placement.site_category, text)


def _render_cat(cat, text):
    """그 카테고리(사이트 플랫폼 · 글 모양)에 맞는 (미리보기 HTML, 서식 복사용 HTML, 글자만, 복사용 HTML).
    네이버는 네이버 글쓰기와, 티스토리·블로거는 티스토리 글쓰기와 같은 인라인 style HTML 을 쓴다.
    꾸밈 없는 HTML 을 붙이면 표 테두리·머리글 색이 빠지고 머리글 줄이 표 밖으로 빠진다 (2026-10-20 사용자).
    워드프레스는 class HTML + 글모양 CSS (블록 에디터가 인라인 style 을 지운다, wp_looks — 2026-10-26)."""
    platform = cat.blog.platform
    if platform == Blog.Platform.NAVER:  # 미리보기도 붙여넣을 HTML 그대로 (문단 사이 빈 줄까지 네이버와 같게)
        from apps.naver_writing.render import CONVERT_FONT, needs_gaps, paste_html, plain_text, render_body
        html = render_body(text)
        rich = paste_html(html, gaps=needs_gaps(text, html), font=CONVERT_FONT)
        return rich, rich, plain_text(html), paste.clean_html(text)
    from apps.writing.render import plain_text, render_body, tistory_align, tistory_html
    if platform == Blog.Platform.WORDPRESS:
        from . import wp_looks
        look = _look(cat)
        html = wp_looks.render(text, look)
        return wp_looks.preview_html(text, look), html, plain_text(html), wp_looks.paste_html(text, look)
    look = _look(cat)
    html = render_body(looks.yudi_source(text) if look == "yudi" else text)
    out = tistory_html(html)  # 문단 사이 빈 줄 · 사진 가운데 620 (2026-10-22). 미리보기도 붙여넣을 HTML 그대로
    if look == "yudi":  # 유디 메모지 (2026-10-23 사용자, 눈잎 › 일본 여행)
        out = looks.yudi_html(out)
    elif _heading_bar(cat):
        out = re.sub(r"<h2(?![^>]*\bstyle=)", f'<h2 style="{HEADING_BAR}"', out)
    if platform == Blog.Platform.TISTORY:  # 사진·캡션 가운데 정렬이 붙여넣을 때 풀리지 않게 (2026-10-25)
        out = tistory_align(out)
    return out, out, plain_text(html), out


# 소제목 앞 빨간 세로 막대 (2026-10-23 사용자, memorily › AI): 크기·말은 그대로, 막대만. 카테고리의 '소제목 빨간 막대'를 켠 곳만.
HEADING_BAR = "border-left:5px solid #e03131;padding-left:12px"


def _heading_bar(cat):
    return cat.heading_bar or bool(cat.parent_id and cat.parent.heading_bar)


def _look(cat):
    return cat.look or (cat.parent.look if cat.parent_id else "")


def _tags_for(placement):
    """태그 칸에 붙일 꼴. 네이버는 '#태그 #태그' (쉼표로 붙이면 한 태그로 붙는다), 블로거는 앞 5개만 (라벨, 2026-10-22 사용자),
    나머지는 쉼표 그대로."""
    platform = placement.site_category.blog.platform
    if platform == Blog.Platform.NAVER:
        from apps.naver_writing.render import tag_line
        return tag_line(placement.converted_tags)
    if platform == Blog.Platform.BLOGGER:
        from .prompt import BLOGGER_LABELS
        labels = [t.strip() for t in placement.converted_tags.split(",") if t.strip()]
        return ", ".join(labels[:BLOGGER_LABELS])
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
    platform = placement.site_category.blog.platform
    naver = platform == Blog.Platform.NAVER
    one_shot = rich and platform in (Blog.Platform.TISTORY, Blog.Platform.NAVER, Blog.Platform.BLOGGER)  # 한 번에 넣기
    return {
        "pl": placement, "blog": placement.site_category.blog, "post": post,
        "form": form or ConvertForm(instance=placement),
        "original_html": render_body(post.body), "converted_html": conv_html, "paste_html": rich, "plain_text": plain,
        "clean_html": clean, "paste": paste.for_platform(placement.site_category.blog.platform),
        "is_naver": naver, "tags_copy": _tags_for(placement),
        "flat": placement.site_category.blog.platform in (Blog.Platform.TISTORY, Blog.Platform.BLOGGER),  # 빈 줄로 간격
        "tag_items": [t.lstrip("#") for t in _tags_for(placement).split()] if naver else [],
        "tag_bookmarklet": paste.naver_tag_bookmarklet(),
        "paste_all": paste.paste_all(placement.converted_title or post.title, rich, _tags_for(placement)) if one_shot else "",
        "paste_bookmarklet": paste.paste_bookmarklet() if one_shot else "",
        "check_html": _check_html(placement.converted_check),
        "request_text": prompt.build(placement),
        "hero": _hero(placement.converted_body) if placement.site_category.blog.platform == Blog.Platform.WORDPRESS else None,
    }


# 대표 사진 내려받기 (2026-10-26 사용자, 워드프레스): 대표 이미지는 미디어 라이브러리에 올린 사진만 고를 수 있어
# 변환본의 첫 사진을 파일로 내려받아 '대표 이미지 설정 → 파일 업로드'에 끌어다 놓는다.
_HERO_MD = re.compile(r"!\[([^\]\n]*)\]\((https?://[^)\s]+)\)")
_HERO_IMG = re.compile(r'<img\b[^>]*?\bsrc="(https?://[^"]+)"[^>]*>')
HERO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
HERO_MAX = 15 * 1024 * 1024


# '한 번에 복사' 뒤 알림 (변환글 보기 _convert_body.html 과 같은 말)
PASTE_MSG = {
    Blog.Platform.NAVER: "복사했습니다. 네이버 글쓰기에서 북마크 → 발행 창 태그 칸을 누르고 북마크 한 번 더.",
    Blog.Platform.BLOGGER: "복사했습니다. 블로거 HTML 보기에서 북마크 → 라벨 칸을 누르고 북마크 한 번 더.",
    Blog.Platform.TISTORY: "복사했습니다. 티스토리 글쓰기(기본모드)에서 북마크를 누르세요.",
}


def paste_data(request, pk):
    """발행예정글 표의 '복사' (2026-10-27 사용자): 변환글 보기의 '한 번에 복사'와 같은 것을 누를 때 받는다.
    표를 열 때 글마다 본문을 그려 두면 느려서, 누른 글만 그린다. html = 서식칸, plain = 북마크가 읽는 글자칸."""
    placement = get_object_or_404(Placement.objects.select_related("site_category__blog", "site_category__parent"), pk=pk)
    platform = placement.site_category.blog.platform
    if platform not in PASTE_MSG or not placement.converted_body.strip():
        return HttpResponseBadRequest("복사할 변환본이 없습니다")
    _, rich, _, _ = _render_for(placement, placement.converted_body)
    title = placement.converted_title or placement.post.title
    return JsonResponse({"html": rich, "plain": paste.paste_all(title, rich, _tags_for(placement)), "msg": PASTE_MSG[platform]},
                        json_dumps_params={"ensure_ascii": False})


def _hero(text):
    """변환본의 첫 사진 {'src', 'alt'} — 없으면 None. 해외여행 글 맨 위 위치 지도는 대표 사진이 아니라 건너뛴다 (2026-10-27)."""
    from urllib.parse import unquote
    text = text or ""
    found = [(m.start(), m[2], m[1]) for m in _HERO_MD.finditer(text)]
    for m in _HERO_IMG.finditer(text):
        alt = re.search(r'\balt="([^"]*)"', m[0])
        found.append((m.start(), m[1], alt[1] if alt else ""))
    for _, src, alt in sorted(found):
        if not unquote(src.split("?", 1)[0]).endswith("/" + prompt.LOCATOR_NAME):
            return {"src": src, "alt": alt.strip()}
    return None


def _hero_name(src, pk, ext=""):
    """내려받을 파일 이름: 주소의 파일 이름(영문·숫자만), 없으면 jinbaam-<매핑 번호>."""
    from urllib.parse import unquote, urlsplit
    base = unquote(urlsplit(src).path.rsplit("/", 1)[-1])
    stem, dot, suffix = base.rpartition(".")
    stem, suffix = (stem, "." + suffix.lower()) if dot and len(suffix) <= 4 else (base, "")
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-")[:60] or f"jinbaam-{pk}"
    return stem + (suffix if suffix in HERO_TYPES.values() or suffix == ".jpeg" else ext or ".jpg")


def hero_photo(request, pk):
    """변환본 첫 사진을 파일로. 저장소의 변환그림은 서버 디스크에서, 다른 주소는 서버가 받아서 넘긴다.
    서버가 받지 못하면 (무료 계정의 외부 접속 제한 등) 그 사진 주소로 보내 브라우저에서 저장하게 한다."""
    placement = get_object_or_404(Placement, pk=pk)
    hero = _hero(placement.converted_body)
    if not hero:
        raise Http404("변환본에 사진이 없습니다.")
    src = hero["src"]
    if src.startswith(prompt.FIGURE_URL):
        from pathlib import Path
        from urllib.parse import unquote
        base = (Path(settings.REPO_ROOT) / prompt.FIGURE_DIR).resolve()
        path = (Path(settings.REPO_ROOT) / unquote(src[len(prompt.FIGURE_URL):].split("?", 1)[0])).resolve()
        if path.is_file() and base in path.parents:
            return FileResponse(path.open("rb"), as_attachment=True, filename=_hero_name(src, pk))
    import urllib.request
    try:
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0 (jb_office)"})
        with urllib.request.urlopen(req, timeout=15) as res:
            ctype = res.headers.get_content_type()
            data = res.read(HERO_MAX + 1)
        if ctype not in HERO_TYPES or len(data) > HERO_MAX:
            raise ValueError(ctype)
    except Exception:
        return redirect(src)
    resp = HttpResponse(data, content_type=ctype)
    resp["Content-Disposition"] = f"attachment; filename=\"{_hero_name(src, pk, HERO_TYPES[ctype])}\""
    return resp


def _panel_context(request, post, nxt):
    pls = list(post.placements.select_related("site_category__blog", "site_category__parent"))
    pick = request.GET.get("pl", "")
    pl = next((x for x in pls if str(x.pk) == pick), pls[0] if pls else None)
    ctx = convert_context(pl) if pl else {"post": post}
    if pl is None:
        from apps.blog_types.views import _site_groups
        from apps.writing.render import render_body
        ctx["original_html"] = render_body(post.body)
        ctx["site_groups"] = sorted(_site_groups(), key=lambda g: g[0] != post.target)  # 여기서 바로 카테고리에 넣는다
        ctx["post_ref"] = request.GET.get("p", "")
    ctx.update({"placements": pls, "next": nxt if nxt.startswith("/") and not nxt.startswith("//") else "",
                "panel_url": f"{reverse('site_templates:panel')}?p={request.GET.get('p')}&next={quote(nxt)}"})
    return ctx


def post_page(request):
    """글 관리 발행예정글의 제목을 누르면 여는 화면 (2026-10-22 사용자): 사이트별 템플릿의 변환 화면 그대로 —
    원문 ↔ 변환본 · 사실 점검 · 붙여넣기 · 변환본 고치기. ?p=tistory:3 [&pl=] [&back=<글 관리 목록 주소>]. 저장하면 이 화면으로."""
    from apps.blog_types.posts import _import_new_drafts, _one
    request.nav_key = "posts_view"
    _import_new_drafts(request)  # 고친 허브 원고를 이 화면에서도 바로 반영한다 (2026-10-27 사용자)
    post = _one(request.GET.get("p"))
    if post is None:
        raise Http404
    back = request.GET.get("back", "")
    back = back if back.startswith("/") and not back.startswith("//") else f"{reverse('posts:view')}?stage={post.stage}"
    ctx = _panel_context(request, post, request.get_full_path())
    ctx.update({"page_title": post.title, "back": back})
    return render(request, "site_templates/post_page.html", ctx)


def panel(request):
    """변환 칸 조각 (2026-10-22): 한 건 보기의 '원문 ↔ 변환본 보기'와 변환 화면의 넣은 곳 고르기가 받아 넣는다.
    ?p=tistory:3 [&pl=<매핑 번호>] [&next=<저장 뒤 돌아갈 주소>]. 넣은 곳이 없으면 원문만, 변환 전이면 변환본은 비어 있다."""
    from apps.blog_types.posts import _one
    post = _one(request.GET.get("p"))
    if post is None:
        return HttpResponse("글을 찾지 못했습니다.", status=404)
    return render(request, "site_templates/_panel.html", _panel_context(request, post, request.GET.get("next", "")))


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

