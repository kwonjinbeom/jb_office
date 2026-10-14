import json
from datetime import date

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.content.models import Content, Folder, Publication
from apps.core.models import AppSetting
from . import ai, services
from .catalog import TEMPLATES, BY_KEY, MANUAL_CHECKS
from .forms import (
    AISettingsForm,
    BackupForm,
    DraftForm,
    NewDraftForm,
    ProfileForm,
    TemplateForm,
)
from .models import Draft, DraftRevision, WritingProfile, WritingTemplate


def nav(request, tab="drafts"):
    request.nav_key = "writing"
    return {"tab": tab, "page_title": "티스토리 글쓰기"}


def get_draft(pk, lock=False):
    qs = Draft.objects.select_related("content", "profile", "content__folder")
    if lock:
        qs = qs.select_for_update()
    return get_object_or_404(qs, pk=pk, content__workspace="blog")


def initial(draft):
    return {
        "title": draft.content.title,
        "body": draft.content.body,
        "status": draft.content.status
        if draft.content.status in ["draft", "review", "ready", "published", "hold"]
        else "draft",
        "folder": draft.content.folder_id,
        "sources": json.dumps(draft.sources, ensure_ascii=False),
        "checks": draft.checks,
        "revision": draft.revision,
        "signature": services.signature(draft.content),
    }


def payload(draft):
    content = services.export_markdown(draft)
    rendered = services.safe_html(content)
    return {
        "revision": draft.revision,
        "signature": services.signature(draft.content),
        "saved_at": timezone.localtime(draft.content.updated_at).strftime("%H:%M:%S"),
        "values": {
            **services.snapshot(draft)["draft"],
            "title": draft.content.title,
            "body": draft.content.body,
            "status": draft.content.status,
            "folder": draft.content.folder_id or "",
            "profile": draft.profile_id or "",
            "published_on": draft.published_on.isoformat()
            if draft.published_on
            else "",
        },
        "html": rendered,
        "plain": services.plain_text(rendered),
        "markdown": content,
        "analysis": services.analysis(draft),
        "prompt": services.prompt(draft),
        "titles": services.title_suggestions(draft),
        "versions": [
            {
                "id": version.pk,
                "label": version.label,
                "time": timezone.localtime(version.created_at).strftime("%m-%d %H:%M"),
            }
            for version in draft.versions.all()[:30]
        ],
    }


def conflict(request, draft):
    try:
        revision = int(request.POST.get("revision", "0"))
    except ValueError:
        revision = 0
    return revision != draft.revision or request.POST.get(
        "signature"
    ) != services.signature(draft.content)


def conflict_response():
    return JsonResponse(
        {
            "error": "다른 화면에서 원고가 바뀌었습니다. 현재 내용을 복사·다운로드한 뒤 최신 원고를 다시 여세요. 편집 내용은 덮어쓰지 않았습니다."
        },
        status=409,
    )


def remember_payload(draft, before, label, throttle=False):
    latest = draft.versions.first()
    if (
        throttle
        and latest
        and (timezone.now() - latest.created_at).total_seconds() < 120
    ):
        return
    DraftRevision.objects.create(draft=draft, label=label, payload=before)
    old = list(draft.versions.values_list("pk", flat=True)[30:])
    if old:
        draft.versions.filter(pk__in=old).delete()


def sync_publication(draft):
    publication = Publication.objects.filter(
        content=draft.content, channel="티스토리"
    ).first()
    if draft.published_url:
        if publication is None:
            publication = Publication(content=draft.content, channel="티스토리")
        if publication.pk is None or draft.content.status == "published":
            publication.title = draft.content.title
        publication.url = draft.published_url
        publication.published_on = draft.published_on
        publication.save()
    elif publication:
        publication.url = ""
        publication.published_on = None
        publication.save(update_fields=["url", "published_on"])


def update_from_form(form, draft):
    for key in ["title", "body", "status"]:
        setattr(draft.content, key, form.cleaned_data[key])
    draft.content.folder = form.cleaned_data["folder"]
    draft.content.summary = draft.answer[:140]
    draft.sources = form.cleaned_data["sources"]
    draft.checks = form.cleaned_data["checks"]


def reset_review_if_changed(before, draft):
    if review_changed(before, draft):
        draft.checks = []
        if (
            before["content"]["status"] == "published"
            and draft.content.status == "published"
        ):
            draft.content.status = "review"


def review_changed(before, draft):
    after = services.snapshot(draft)
    return any(
        before["content"][key] != after["content"][key] for key in ["body", "title"]
    ) or any(
        before["draft"][key] != after["draft"][key]
        for key in [
            "sources",
            "question",
            "answer",
            "experience",
            "profile_id",
            "template_key",
            "commercial",
        ]
    )


def draft_list(request):
    ctx = nav(request)
    q, status = request.GET.get("q", "").strip(), request.GET.get("status", "")
    qs = Draft.objects.filter(content__workspace="blog").select_related(
        "content", "profile"
    )
    if q:
        qs = qs.filter(
            Q(content__title__icontains=q)
            | Q(keyword__icontains=q)
            | Q(content__body__icontains=q)
        )
    if status in dict(Content.Status.choices):
        qs = qs.filter(content__status=status)
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    ctx.update(
        page=page,
        total=Draft.objects.filter(content__workspace="blog").count(),
        q=q,
        status=status,
        statuses=[
            (v, l)
            for v, l in Content.Status.choices
            if v in ["draft", "review", "ready", "published", "hold"]
        ],
        profiles=WritingProfile.objects.all(),
    )
    return render(request, "writing/list.html", ctx)


def create(request):
    ctx = nav(request)
    form = NewDraftForm(
        request.POST if request.method == "POST" else None,
        initial={"template_key": request.GET.get("template", "howto")},
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            content = Content.objects.create(
                workspace="blog",
                kind="work",
                status="draft",
                title=form.cleaned_data["title"],
                folder=form.cleaned_data["folder"],
            )
            draft = Draft.objects.create(
                content=content,
                profile=form.cleaned_data["profile"],
                template_key=form.cleaned_data["template_key"],
            )
        return redirect(draft)
    ctx.update(form=form, page_title="새 원고", cancel_url=reverse("writing:list"))
    return render(request, "writing/form.html", ctx)


def editor(request, pk):
    ctx = nav(request)
    if request.method == "POST":
        # JavaScript가 꺼져 있어도 저장할 수 있다.
        with transaction.atomic():
            draft = get_draft(pk, lock=True)
            if conflict(request, draft):
                form = DraftForm(request.POST, instance=draft)
                form.is_valid()
                form.add_error(
                    None,
                    "다른 화면에서 바뀐 원고입니다. 입력 내용은 아래에 유지했습니다. 내용을 보관하고 최신 화면을 다시 여세요.",
                )
            else:
                before = services.snapshot(draft)
                form = DraftForm(request.POST, instance=draft)
                if form.is_valid():
                    update_from_form(form, draft)
                    reset_review_if_changed(before, draft)
                    if before != services.snapshot(draft):
                        remember_payload(draft, before, "직접 저장 전")
                        draft.revision += 1
                        draft.content.save()
                        draft.save()
                        sync_publication(draft)
                    messages.success(request, "원고를 저장했습니다.")
                    return redirect(draft)
    else:
        draft = get_draft(pk)
        form = DraftForm(instance=draft, initial=initial(draft))
    key, _ = ai.configuration()
    ctx.update(
        draft=draft,
        form=form,
        page_title=draft.content.title,
        current_template=services.template(draft),
        bundle=payload(draft),
        manual_checks=MANUAL_CHECKS,
        versions=draft.versions.all()[:30],
        ai_configured=bool(key),
        editor_url=(
            draft.profile.blog_url.rstrip("/") + "/manage/newpost/"
            if draft.profile and draft.profile.blog_url
            else "https://www.tistory.com"
        ),
    )
    return render(request, "writing/editor.html", ctx)


@require_POST
def save(request, pk):
    with transaction.atomic():
        draft = get_draft(pk, lock=True)
        if conflict(request, draft):
            return conflict_response()
        before = services.snapshot(draft)
        form = DraftForm(request.POST, instance=draft)
        if not form.is_valid():
            return JsonResponse(
                {
                    "error": "입력 항목을 확인하세요. 원고는 저장하지 않았습니다.",
                    "errors": form.errors.get_json_data(),
                },
                status=400,
            )
        update_from_form(form, draft)
        reset_review_if_changed(before, draft)
        if before != services.snapshot(draft):
            remember_payload(
                draft,
                before,
                "자동 저장 전" if request.POST.get("autosave") else "직접 저장 전",
                throttle=bool(request.POST.get("autosave")),
            )
            draft.revision += 1
            draft.content.save()
            draft.save()
            sync_publication(draft)
    return JsonResponse(payload(draft))


@require_POST
def preview(request, pk):
    draft = get_draft(pk)
    form = DraftForm(request.POST, instance=draft)
    if not form.is_valid():
        return JsonResponse(
            {"error": "입력 항목을 확인하세요.", "errors": form.errors.get_json_data()},
            status=400,
        )
    update_from_form(form, draft)
    return JsonResponse(payload(draft))


@require_POST
def action(request, pk):
    action_name = request.POST.get("action")
    if action_name == "ai":
        draft = get_draft(pk)
        if conflict(request, draft):
            return conflict_response()
        if not draft.question.strip() or not draft.answer.strip():
            return JsonResponse(
                {"error": "독자의 질문과 핵심 답을 먼저 적어 주세요."}, status=400
            )
        try:
            generated = ai.generate(draft)
        except ai.AIError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        with transaction.atomic():
            draft = get_draft(pk, lock=True)
            if conflict(request, draft):
                return JsonResponse(
                    {
                        "error": "AI 생성 중 원고가 바뀌어 결과를 덮어쓰지 않았습니다. 생성 결과는 복사해서 사용할 수 있습니다.",
                        "generated": generated,
                    },
                    status=409,
                )
            services.remember(draft, "AI 초안 생성 전")
            draft.content.title, draft.content.body = (
                generated["title"],
                generated["body"],
            )
            if draft.content.status == "published":
                draft.content.status = "review"
            draft.description, draft.tags = generated["description"], generated["tags"]
            draft.checks = []
            draft.revision += 1
            draft.content.save()
            draft.save()
        return JsonResponse(payload(draft))
    with transaction.atomic():
        draft = get_draft(pk, lock=True)
        if conflict(request, draft):
            return conflict_response()
        if action_name == "scaffold":
            services.remember(draft, "구성 만들기 전")
            draft.content.body = services.scaffold(draft)
            draft.checks = []
            if draft.content.status == "published":
                draft.content.status = "review"
        elif action_name == "restore":
            version = get_object_or_404(
                DraftRevision, draft=draft, pk=request.POST.get("version")
            )
            services.remember(draft, "이전 버전 복구 전")
            data = version.payload
            for key in services.CONTENT_FIELDS:
                if key != "folder_id":
                    setattr(draft.content, key, data["content"][key])
            draft.content.folder = Folder.objects.filter(
                pk=data["content"].get("folder_id"), workspace="blog"
            ).first()
            for key in services.DRAFT_FIELDS:
                if key != "profile_id":
                    setattr(draft, key, data["draft"][key])
            draft.profile = WritingProfile.objects.filter(
                pk=data["draft"].get("profile_id")
            ).first()
            draft.published_on = (
                date.fromisoformat(data["published_on"])
                if data.get("published_on")
                else None
            )
        else:
            return JsonResponse({"error": "알 수 없는 작업입니다."}, status=400)
        draft.revision += 1
        draft.content.save()
        draft.save()
        sync_publication(draft)
    return JsonResponse(payload(draft))


def download(request, pk, kind):
    draft = get_draft(pk)
    if kind == "html":
        text, mime = services.safe_html(services.export_markdown(draft)), "text/html"
    elif kind == "md":
        text, mime = (
            f"# {draft.content.title}\n\n" + services.export_markdown(draft),
            "text/markdown",
        )
    else:
        text, mime = (
            json.dumps(services.snapshot(draft), ensure_ascii=False, indent=2),
            "application/json",
        )
        kind = "json"
    response = HttpResponse(text, content_type=mime + "; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="tistory-{draft.pk}.{kind}"'
    )
    return response


@require_POST
def duplicate(request, pk):
    draft = get_draft(pk)
    with transaction.atomic():
        data = services.snapshot(draft)
        content_data = data["content"]
        content_data.update(
            title=(content_data["title"][:150] + " · 복사"), status="draft"
        )
        content = Content.objects.create(workspace="blog", kind="work", **content_data)
        fields = data["draft"]
        fields.update(checks=[], published_url="")
        copied = Draft.objects.create(content=content, **fields)
    return redirect(copied)


@require_POST
def attach(request, content_pk):
    content = get_object_or_404(Content, pk=content_pk, workspace="blog", kind="work")
    draft, _ = Draft.objects.get_or_create(
        content=content, defaults={"answer": content.summary}
    )
    return redirect(draft)


def delete(request, pk):
    draft = get_draft(pk)
    if request.method == "POST":
        draft.content.delete()
        return redirect("writing:list")
    return render(
        request,
        "content/delete.html",
        {
            **nav(request),
            "page_title": "원고 삭제",
            "object_title": draft.content.title,
            "cancel_url": draft.get_absolute_url(),
        },
    )


def templates(request):
    return render(
        request,
        "writing/templates.html",
        {
            **nav(request, "templates"),
            "builtins": TEMPLATES,
            "custom_templates": WritingTemplate.objects.all(),
        },
    )


def template_form(request, pk=None):
    item = get_object_or_404(WritingTemplate, pk=pk) if pk else WritingTemplate()
    base = BY_KEY.get(request.GET.get("base"))
    initial_values = (
        {
            "name": base["name"] + " · 내 방식",
            "description": base["description"],
            "body": base["body"],
        }
        if base and not pk
        else None
    )
    form = TemplateForm(
        request.POST if request.method == "POST" else None,
        instance=item,
        initial=initial_values,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("writing:templates")
    return render(
        request,
        "writing/form.html",
        {
            **nav(request, "templates"),
            "page_title": "템플릿 수정" if pk else "내 템플릿 만들기",
            "form": form,
            "cancel_url": reverse("writing:templates"),
        },
    )


def settings_view(request):
    key, model = ai.configuration()
    form = AISettingsForm(
        request.POST if request.method == "POST" else None, initial={"model": model}
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            if form.cleaned_data["remove_key"]:
                AppSetting.set(ai.KEY_SETTING, "")
            elif form.cleaned_data["api_key"]:
                AppSetting.set(ai.KEY_SETTING, form.cleaned_data["api_key"])
            AppSetting.set(ai.MODEL_SETTING, form.cleaned_data["model"])
        messages.success(request, "AI 작성 설정을 저장했습니다.")
        return redirect("writing:settings")
    return render(
        request,
        "writing/settings.html",
        {
            **nav(request, "settings"),
            "profiles": WritingProfile.objects.all(),
            "form": form,
            "ai_configured": bool(key),
        },
    )


def profile_form(request, pk=None):
    profile = get_object_or_404(WritingProfile, pk=pk) if pk else WritingProfile()
    form = ProfileForm(
        request.POST if request.method == "POST" else None, instance=profile
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("writing:settings")
    return render(
        request,
        "writing/form.html",
        {
            **nav(request, "settings"),
            "page_title": "작성 규칙 수정" if pk else "작성 규칙 추가",
            "form": form,
            "cancel_url": reverse("writing:settings"),
        },
    )


def config_delete(request, pk, kind):
    model = WritingProfile if kind == "profile" else WritingTemplate
    item = get_object_or_404(model, pk=pk)
    tab = "settings" if kind == "profile" else "templates"
    if request.method == "POST":
        item.delete()
        return redirect(f"writing:{tab}")
    return render(
        request,
        "writing/config_delete.html",
        {
            **nav(request, tab),
            "item": item,
            "kind": kind,
            "cancel_url": reverse(f"writing:{tab}"),
        },
    )


def import_backup(request):
    form = BackupForm(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        backup = form.cleaned_data["file"]
        data = backup["draft"]

        def valid_id(value):
            return (
                int(value)
                if isinstance(value, (int, str)) and str(value).isdigit()
                else None
            )

        profile = WritingProfile.objects.filter(
            pk=valid_id(data.get("profile_id"))
        ).first()
        folder = Folder.objects.filter(
            pk=valid_id(backup["content"].get("folder_id")), workspace="blog"
        ).first()
        key = data.get("template_key", "howto")
        available = {t["key"] for t in TEMPLATES} | {
            f"custom:{t.pk}" for t in WritingTemplate.objects.all()
        }
        values = {
            "title": backup["content"]["title"],
            "body": backup["content"]["body"],
            "template_key": key
            if isinstance(key, str) and key in available
            else "howto",
            "profile": profile.pk if profile else "",
            "folder": folder.pk if folder else "",
            "status": "draft",
            "revision": 1,
            "signature": "import",
            "sources": json.dumps(data.get("sources", [])),
            "checks": [],
        }
        for name in [
            "keyword",
            "tags",
            "question",
            "answer",
            "experience",
            "description",
        ]:
            values[name] = data.get(name, "")
        if data.get("commercial") is True:
            values["commercial"] = "on"
        content = Content(workspace="blog", kind="work", status="draft")
        draft = Draft(content=content)
        draft_form = DraftForm(values, instance=draft)
        if draft_form.is_valid():
            with transaction.atomic():
                update_from_form(draft_form, draft)
                content.save()
                draft.content = content
                draft.save()
            messages.success(request, "백업을 새 원고로 불러왔습니다.")
            return redirect(draft)
        for errors in draft_form.errors.values():
            for message in errors:
                form.add_error("file", message)
    return render(
        request,
        "writing/form.html",
        {
            **nav(request),
            "page_title": "원고 백업 가져오기",
            "form": form,
            "cancel_url": reverse("writing:list"),
        },
    )
