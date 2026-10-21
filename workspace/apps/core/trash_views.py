import json

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import TrashEntry
from .trash import TrashError, _collect, hide_source, model_for, move_to_trash, restore, title_for


def index(request):
    request.nav_key = "trash"
    query = request.GET.get("q", "").strip()[:200]
    section = request.GET.get("section", "")
    items = TrashEntry.objects.all()
    sections = list(items.order_by("section").values_list("section", flat=True).distinct())
    if query:
        items = items.filter(Q(title__icontains=query) | Q(section__icontains=query))
    if section:
        items = items.filter(section=section)
    return render(request, "core/trash.html", {
        "page_title": "휴지통", "page": Paginator(items, 50).get_page(request.GET.get("page")),
        "total": TrashEntry.objects.count(), "q": query, "section": section, "sections": sections,
    })


def _payload(request):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise TrashError("요청 내용을 확인하세요.")
    if not isinstance(data, dict):
        raise TrashError("요청 내용을 확인하세요.")
    return data


def _targets(request):
    items = _payload(request).get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= 200:
        raise TrashError("한 번에 1~200개를 선택하세요.")
    found, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            raise TrashError("선택한 항목을 확인하세요.")
        label, key = item.get("model"), item.get("id")
        if not isinstance(label, str) or not isinstance(key, (str, int)) or len(str(key)) > 512:
            raise TrashError("선택한 항목을 확인하세요.")
        key = str(key)
        if (label, key) in seen:
            continue
        seen.add((label, key))
        if label.startswith("source."):
            kind = label.split(".", 1)[1]
            if kind == "daily":
                from apps.daily_ideas.data import find_item
                source = find_item(key)
                if source is None:
                    raise TrashError("일일 아이디어를 찾을 수 없습니다.")
                title = source["title"]
            elif kind == "docs":
                from apps.docs.views import _resolve
                try:
                    title = _resolve(key).stem
                except Http404:
                    raise TrashError("문서를 찾을 수 없습니다.")
            else:
                raise TrashError("삭제할 수 없는 자료입니다.")
            found.append((label, key, title, None))
        else:
            model = model_for(label)
            if not key.isdigit():
                raise TrashError("항목 번호를 확인하세요.")
            fields = {f.name for f in model._meta.fields}
            obj = model.objects.only(*sorted(fields & {"id", "title", "name", "channel", "body", "version", "workspace", "stage"} - {"body"})).filter(pk=int(key)).first()
            if obj is None:
                raise TrashError("항목이 이미 이동되었거나 삭제되었습니다. 새로고침 후 확인하세요.")
            found.append((label, key, title_for(obj), obj))
    return found


@require_POST
def preview(request):
    try:
        targets = _targets(request)
        graph = {}
        sources = set()
        for label, key, title, obj in targets:
            if obj:
                for related, ids in _collect(type(obj), [obj.pk]).items():
                    graph.setdefault(related, set()).update(ids)
            else:
                sources.add((label, key))
        count = sum(len(ids) for ids in graph.values()) + len(sources)
        return JsonResponse({"ok": True, "count": count, "selected": len(targets),
                             "title": targets[0][2], "has_sources": bool(sources)})
    except TrashError as error:
        return JsonResponse({"ok": False, "error": str(error)}, status=400)


@require_POST
def move(request):
    try:
        with transaction.atomic():
            targets = _targets(request)
            entries = []
            for label, key, title, obj in targets:
                entry = move_to_trash(obj) if obj else hide_source(label.split(".", 1)[1], key, title)
                if entry:
                    entries.append(entry.pk)
        return JsonResponse({"ok": True, "entries": entries, "count": len(entries)})
    except TrashError as error:
        return JsonResponse({"ok": False, "error": str(error)}, status=400)


@require_POST
def restore_items(request):
    try:
        ids = _payload(request).get("ids")
        if not isinstance(ids, list) or not 1 <= len(ids) <= 200 or any(not str(pk).isdigit() for pk in ids):
            raise TrashError("복원할 항목을 선택하세요.")
        with transaction.atomic():
            entries = list(TrashEntry.objects.filter(pk__in=ids).order_by("deleted_at", "pk"))
            if not entries:
                raise TrashError("항목이 이미 복원되었거나 보관 기간이 지났습니다.")
            # Retry children after their independently deleted parents in the same selection.
            pending = entries
            while pending:
                deferred, progressed = [], False
                for entry in pending:
                    try:
                        restore(entry)
                        progressed = True
                    except TrashError:
                        deferred.append(entry)
                if deferred and not progressed:
                    restore(deferred[0])
                pending = deferred
        return JsonResponse({"ok": True, "count": len(entries)})
    except TrashError as error:
        return JsonResponse({"ok": False, "error": str(error)}, status=400)
