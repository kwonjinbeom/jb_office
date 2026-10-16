from datetime import date, timedelta

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.content.tree import decorate_tree, subtree_ids
from apps.content.navigation import list_return
from apps.core.menus import find_menu
from . import docs
from .forms import DiscussionForm, QuickForm
from .models import Discussion, DiscussionHistory


SNAPSHOT_FIELDS = ["summary", "next_action", "status", "amount", "partner"]

# 메뉴 하나의 '논의 현황'이 대구분 여럿을 묶는 경우 (아이디어 = 일일 아이디어 + 내 아이디어)
AREA_GROUPS = {"idea": ("아이디어", ["daily_ideas", "ideas"])}
GROUP_OF = {a: g for g, (_, areas) in AREA_GROUPS.items() for a in areas}


def _areas(area):
    """화면의 area(?area=) → 실제 대구분 목록."""
    if area in AREA_GROUPS:
        return AREA_GROUPS[area][1]
    return [area] if area in dict(Discussion.AREA_CHOICES) else []


def _nav(request, area):
    """블로그·카페·영상 콘텐츠의 논의는 그 메뉴 아래 '논의 현황'으로, 그 밖에는 '진행현황'으로 강조한다.

    하위 메뉴가 있는 area 면 그 메뉴(Menu)를 돌려준다. key 규칙: "<area>_discussions" (apps/core/menus.py).
    """
    menu = find_menu(f"{GROUP_OF.get(area, area)}_discussions") if area else None
    if menu:
        request.nav_key = menu.key
    return menu


def _list_url(area=""):
    url = reverse("discussions:list")
    area = GROUP_OF.get(area, area)
    return f"{url}?area={area}" if find_menu(f"{area}_discussions") else url


def save_form(form):
    with transaction.atomic():
        item = form.save()
        latest = item.history.first()
        snapshot = {field: getattr(item, field) for field in SNAPSHOT_FIELDS}
        if latest is None or any(getattr(latest, field) != value for field, value in snapshot.items()):
            DiscussionHistory.objects.create(discussion=item, **snapshot)
        return item


WEEKDAYS = "월화수목금토일"
PERIODS = [("today", "오늘", 0), ("7", "7일", 6), ("30", "30일", 29)]


def _parse_day(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _day_label(day, today):
    if day == today:
        return "오늘"
    if day == today - timedelta(days=1):
        return "어제"
    return f"{day.month}월 {day.day}일 ({WEEKDAYS[day.weekday()]})" + (f" · {day.year}" if day.year != today.year else "")


def discussion_list(request):
    docs.sync()  # 저장소의 논의 글(논의/**/*.md)을 먼저 맞춘다
    nodes = decorate_tree(Discussion.objects.all())
    q, area, status = [request.GET.get(key, "").strip() for key in ("q", "area", "status")]
    scope_areas = _areas(area)
    selected = next((node for node in nodes if str(node.pk) == request.GET.get("topic") and (not area or node.area in scope_areas)), None)
    today = timezone.localdate()

    # 기간: period(오늘·7일·30일) 또는 from~to. 그 기간에 바뀐 논의 = 최근 변경이 그 안이거나, 그 안에 요약 이력이 있는 것.
    period = request.GET.get("period", "")
    days_back = next((back for key, _, back in PERIODS if key == period), None)
    if days_back is not None:
        date_from, date_to = today - timedelta(days=days_back), today
    else:
        period = ""
        date_from, date_to = _parse_day(request.GET.get("from", "")), _parse_day(request.GET.get("to", ""))
        if date_from and date_to and date_from > date_to:
            date_from, date_to = date_to, date_from

    qs = Discussion.objects.all()
    if scope_areas:
        qs = qs.filter(area__in=scope_areas)
    if selected:
        qs = qs.filter(pk__in=subtree_ids(nodes, selected.pk))
    if status in Discussion.Status.values:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(summary__icontains=q) | Q(next_action__icontains=q) | Q(history__summary__icontains=q))
    if date_from or date_to:
        touched, logged = Q(), Q()
        if date_from:
            touched &= Q(updated_at__date__gte=date_from)
            logged &= Q(history__created_at__date__gte=date_from)
        if date_to:
            touched &= Q(updated_at__date__lte=date_to)
            logged &= Q(history__created_at__date__lte=date_to)
        qs = qs.filter(touched | logged)
    qs = qs.distinct().order_by("-updated_at", "-pk")  # 최신 변경이 위로

    by_id = {node.pk: node for node in nodes}
    entries = list(qs)
    day_groups = []
    for entry in entries:
        entry.path = by_id[entry.pk].path
        entry.group_path = " / ".join(entry.path.split(" / ")[:-1])  # 중구분 (상위 주제들)
        day = timezone.localtime(entry.updated_at).date()
        if not day_groups or day_groups[-1]["day"] != day:
            day_groups.append({"day": day, "label": _day_label(day, today), "entries": []})
        day_groups[-1]["entries"].append(entry)

    scope = _nav(request, area)
    scope_label = (AREA_GROUPS[area][0] if area in AREA_GROUPS else dict(Discussion.AREA_CHOICES)[area]) if scope else ""
    return render(request, "discussions/list.html", {
        "page_title": f"{scope_label} 논의 현황" if scope else "진행현황", "scope": scope, "scope_label": scope_label,
        "entries": entries, "day_groups": day_groups,
        "topics": [node for node in nodes if not area or node.area in scope_areas], "selected": selected,
        "q": q, "area": area, "status": status, "areas": Discussion.AREA_CHOICES, "statuses": Discussion.Status.choices,
        "period": period, "periods": PERIODS, "date_from": date_from.isoformat() if date_from else "", "date_to": date_to.isoformat() if date_to else "",
        "today": today, "is_filtered": bool(q or status or selected or date_from or date_to or (area and not scope)),
    })


def discussion_detail(request, pk):
    docs.sync()
    item = get_object_or_404(Discussion.objects.select_related("idea", "content", "parent"), pk=pk)
    nodes = decorate_tree(Discussion.objects.all())
    path = next(node.path for node in nodes if node.pk == pk)
    return render(request, "discussions/detail.html", {"page_title": item.name, "scope": _nav(request, item.area), "list_url": _list_url(item.area), "post": docs.post(item), "statuses": Discussion.Status.choices, "item": item, "path": path, "history": item.history.all(), "children": item.children.all()})


def discussion_form(request, pk=None):
    with transaction.atomic():
        item = get_object_or_404(Discussion.objects.select_for_update(), pk=pk) if pk else Discussion()
        initial = {}
        if not pk:
            parent = Discussion.objects.filter(pk=request.GET.get("parent")).first() if request.GET.get("parent", "").isdigit() else None
            if parent:
                initial.update(parent=parent, area=parent.area)
            elif request.GET.get("area") in dict(Discussion.AREA_CHOICES):
                initial["area"] = request.GET["area"]
        form = DiscussionForm(request.POST if request.method == "POST" else None, instance=item, initial=initial)
        area = item.area if pk else initial.get("area", "")
        _nav(request, area)
        if request.method == "POST" and form.is_valid():
            messages.success(request, "핵심을 저장했습니다.")
            return redirect(save_form(form))
    return render(request, "content/form.html", {"page_title": "논의 수정" if pk else "새 논의 주제", "form": form, "cancel_url": item.get_absolute_url() if pk else _list_url(area)})


@require_POST
def quick_update(request, pk):
    with transaction.atomic():
        item = get_object_or_404(Discussion.objects.select_for_update(), pk=pk)
        form = QuickForm(request.POST, instance=item)
        if form.is_valid():
            save_form(form)
        else:
            messages.error(request, "저장하지 못했습니다. 핵심은 140자, 다음 행동은 80자 이내로 적고 상태를 선택하세요.")
    if request.POST.get("return_to") == item.get_absolute_url():  # 상세 화면에서 고친 경우
        return redirect(item)
    return redirect(list_return(request, reverse("discussions:list")))


def asset(request, rel):
    """논의 글 옆에 둔 그림 파일."""
    path = docs.asset_path(rel)
    if path is None:
        raise Http404
    return FileResponse(path.open("rb"), content_type=docs.IMAGE_TYPES[path.suffix.lower()])


def discussion_delete(request, pk):
    item = get_object_or_404(Discussion, pk=pk)
    _nav(request, item.area)
    if request.method == "POST":
        back = _list_url(item.area)
        try:
            item.delete()
        except ProtectedError:
            messages.error(request, "하위 주제를 먼저 옮기거나 삭제하세요.")
            return redirect(item)
        return redirect(back)
    return render(request, "content/delete.html", {"page_title": "논의 삭제", "object_title": item.name, "cancel_url": item.get_absolute_url()})
