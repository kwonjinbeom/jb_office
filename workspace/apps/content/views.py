from django.contrib import messages
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ContentForm, FolderForm, PublicationForm
from .models import Content, Folder, Publication, Workspace
from .navigation import list_return
from .tree import decorate_tree, subtree_ids


def context(request):
    space = request.resolver_match.app_name
    return {"space": space, "page_title": Workspace(space).label, "list_url": reverse(f"{space}:list")}


def content_list(request):
    ctx = context(request)
    space = ctx["space"]
    folders = decorate_tree(Folder.objects.filter(workspace=space))
    selected = next((f for f in folders if str(f.pk) == request.GET.get("folder")), None)
    qs = Content.objects.filter(workspace=space).select_related("folder")
    q = request.GET.get("q", "").strip()
    status, kind = request.GET.get("status", ""), request.GET.get("kind", "")
    if selected:
        qs = qs.filter(folder_id__in=subtree_ids(folders, selected.pk))
    elif request.GET.get("folder") == "none":
        qs = qs.filter(folder__isnull=True)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(body__icontains=q) | Q(outline__icontains=q) | Q(scenes__icontains=q))
    if status in Content.Status.values:
        qs = qs.filter(status=status)
    if kind in Content.Kind.values:
        qs = qs.filter(kind=kind)
    paths = {f.pk: f.path for f in folders}
    entries = list(qs)
    for entry in entries:
        entry.folder_path = paths.get(entry.folder_id, "미분류")
    ctx.update(entries=entries, folders=folders, selected=selected, folder_filter=request.GET.get("folder", ""), q=q, status=status, kind=kind, statuses=Content.Status.choices, kinds=Content.Kind.choices,
               children=[f for f in folders if f.parent_id == (selected.pk if selected else None)],
               create_url=reverse(f"{space}:create"), folder_create_url=reverse(f"{space}:folder_create"))
    return render(request, "content/list.html", ctx)


def content_detail(request, pk):
    ctx = context(request)
    item = get_object_or_404(Content.objects.select_related("folder", "idea"), pk=pk, workspace=ctx["space"])
    ctx.update(item=item, page_title=item.title, publications=item.publications.all())
    return render(request, "content/detail.html", ctx)


def content_form(request, pk=None):
    ctx = context(request)
    item = get_object_or_404(Content, pk=pk, workspace=ctx["space"]) if pk else Content(workspace=ctx["space"])
    initial = {}
    if not pk:
        folder = Folder.objects.filter(pk=request.GET.get("folder"), workspace=ctx["space"]).first() if request.GET.get("folder", "").isdigit() else None
        initial["folder"] = folder
        if request.GET.get("template", "").isdigit():
            template = get_object_or_404(Content, pk=request.GET["template"], workspace=ctx["space"], kind=Content.Kind.TEMPLATE)
            initial.update(folder=template.folder, kind=Content.Kind.WORK, status=Content.Status.DRAFT, outline=template.outline, body=template.body, scenes=template.scenes)
    form = ContentForm(request.POST if request.method == "POST" else None, instance=item, workspace=ctx["space"], initial=initial)
    if request.method == "POST" and form.is_valid():
        messages.success(request, "저장했습니다.")
        return redirect(form.save())
    ctx.update(form=form, page_title="콘텐츠 수정" if pk else "새 콘텐츠", cancel_url=item.get_absolute_url() if pk else ctx["list_url"])
    return render(request, "content/form.html", ctx)


def folder_form(request, pk=None):
    ctx = context(request)
    folder = get_object_or_404(Folder, pk=pk, workspace=ctx["space"]) if pk else Folder(workspace=ctx["space"])
    parent = Folder.objects.filter(pk=request.GET.get("parent"), workspace=ctx["space"]).first() if request.GET.get("parent", "").isdigit() else None
    form = FolderForm(request.POST if request.method == "POST" else None, instance=folder, workspace=ctx["space"], initial={"parent": parent} if not pk else None)
    if request.method == "POST" and form.is_valid():
        return redirect(form.save())
    ctx.update(form=form, page_title="폴더 설정" if pk else "새 폴더", cancel_url=folder.get_absolute_url() if pk else ctx["list_url"])
    return render(request, "content/form.html", ctx)


def publication_form(request, content_pk, pk=None):
    ctx = context(request)
    content = get_object_or_404(Content, pk=content_pk, workspace=ctx["space"])
    publication = get_object_or_404(Publication, pk=pk, content=content) if pk else Publication(content=content)
    form = PublicationForm(request.POST if request.method == "POST" else None, instance=publication)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(content)
    ctx.update(form=form, page_title="게시처별 버전·기록", cancel_url=content.get_absolute_url())
    return render(request, "content/form.html", ctx)


@require_POST
def status_update(request, pk):
    ctx = context(request)
    item = get_object_or_404(Content, pk=pk, workspace=ctx["space"])
    status = request.POST.get("status")
    if status not in Content.Status.values:
        messages.error(request, "올바른 상태를 선택하세요.")
    else:
        item.status = status
        item.save(update_fields=["status", "updated_at"])
    return redirect(list_return(request, ctx["list_url"]))


def download(request, pk):
    ctx = context(request)
    item = get_object_or_404(Content.objects.select_related("folder"), pk=pk, workspace=ctx["space"])
    sections = [f"# {item.title}", f"공간: {item.get_workspace_display()} · 종류: {item.get_kind_display()} · 상태: {item.get_status_display()}"]
    for label, value in [("핵심", item.summary), ("기획·구성", item.outline), ("본문·대본", item.body), ("자료·장면", item.scenes)]:
        if value:
            sections.append(f"## {label}\n\n{value}")
    for publication in item.publications.all():
        sections.append(f"## 게시처: {publication.channel}\n\n{publication.title}\n\n{publication.version}\n\nURL: {publication.url or '-'}\n게시일: {publication.published_on or '-'}\n반응: {publication.result or '-'}")
    response = HttpResponse("\n\n".join(sections) + "\n", content_type="text/markdown; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{item.workspace}-{item.pk}.md"'
    return response


def delete(request, pk, target="content", content_pk=None):
    ctx = context(request)
    if target == "folder":
        item = get_object_or_404(Folder, pk=pk, workspace=ctx["space"])
    elif target == "publication":
        item = get_object_or_404(Publication, pk=pk, content_id=content_pk, content__workspace=ctx["space"])
    else:
        item = get_object_or_404(Content, pk=pk, workspace=ctx["space"])
    cancel = item.get_absolute_url()
    if request.method == "POST":
        try:
            item.delete()
        except ProtectedError:
            messages.error(request, "하위 폴더와 콘텐츠를 먼저 옮기거나 삭제하세요.")
            return redirect(cancel)
        return redirect(item.content if target == "publication" else ctx["list_url"])
    ctx.update(page_title="삭제 확인", object_title=getattr(item, "title", None) or getattr(item, "name", None) or item.channel, cancel_url=cancel)
    return render(request, "content/delete.html", ctx)
