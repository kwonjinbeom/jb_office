from __future__ import annotations

import re
from datetime import date, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.inplace import answer
from apps.ideas.models import Idea

from .data import CATEGORY_LABELS, find_item, load_batches
from .forms import StandardForm
from .models import SearchStandard
from .standard import FIELDS as STANDARD_FIELDS
from .standard import defaults as standard_defaults
from .standard import request_text as standard_request
from .standard import to_markdown as standard_to_markdown


CATEGORY_TO_IDEA = {
    "tool": Idea.Category.PRODUCT,
    "service": Idea.Category.REQUEST,
    "search": Idea.Category.SEARCH,
    "content": Idea.Category.SOCIAL,
    "digital": Idea.Category.MARKET,
}


def _matches(item: dict, query: str) -> bool:
    if not query:
        return True
    haystack = " ".join(
        str(item.get(key, ""))
        for key in ("id", "title", "audience", "problem", "min_product", "money_flow", "channel", "evidence", "risk", "tags")
    )
    return query.casefold() in haystack.casefold()


WEEKDAYS = "월화수목금토일"


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _calendar(day: date, selected: str, counts: dict[str, int], today: date) -> dict:
    """위쪽 달력 띠: day 가 들어 있는 한 주(월~일)와 앞뒤로 움직일 날짜."""
    monday = day - timedelta(days=day.weekday())
    days = []
    for offset in range(7):
        current = monday + timedelta(days=offset)
        iso = current.isoformat()
        days.append(
            {
                "iso": iso,
                "day": current.day,
                "weekday": WEEKDAYS[offset],
                "count": counts.get(iso, 0),
                "is_selected": iso == selected,
                "is_today": current == today,
                "is_weekend": offset >= 5,
                "is_future": current > today,
            }
        )
    researched = sorted(counts)
    earlier = [d for d in researched if d < day.isoformat()]
    later = [d for d in researched if d > day.isoformat()]
    sunday = monday + timedelta(days=6)
    week_label = f"{monday.year}년 {monday.month}월"
    if sunday.month != monday.month:
        week_label += f" ~ {sunday.month}월"
    return {
        "days": days,
        "week_label": week_label,
        "prev_week": (day - timedelta(days=7)).isoformat(),
        "next_week": (day + timedelta(days=7)).isoformat(),
        # 좌우 화살표는 조사한 날만 건너다닌다 (빈 날에 멈추지 않게).
        "prev_date": earlier[-1] if earlier else "",
        "next_date": later[0] if later else "",
        "latest": researched[-1] if researched else "",
        "today": today.isoformat(),
        "min": researched[0] if researched else "",
    }


def daily_list(request):
    from apps.core.trash import hidden_keys
    hidden = hidden_keys("daily")
    batches = [{**batch, "items": [item for item in batch["items"] if item["id"] not in hidden]} for batch in load_batches()]
    counts = {batch["date"]: len(batch["items"]) for batch in batches}
    latest = max(counts) if counts else ""
    today = timezone.localdate()

    # date: 없으면 가장 최근 조사일, "all" 이면 전체 기간, 그 밖에는 고른 날짜(조사가 없는 날도 그대로 보여 준다).
    raw_date = request.GET.get("date", "")
    show_all = raw_date == "all"
    picked = None if show_all else _parse_date(raw_date)
    if show_all:
        selected_date = "all"
        anchor = _parse_date(latest) or today
    else:
        anchor = picked or _parse_date(latest) or today
        selected_date = anchor.isoformat()

    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    if category not in CATEGORY_LABELS:
        category = ""

    adopted = {}
    for idea in Idea.objects.filter(tags__contains="daily:").only("id", "code", "title", "tags"):
        for tag in idea.tag_list:
            if tag.startswith("daily:"):
                adopted[tag] = idea

    groups = []
    total = adopted_count = 0
    category_counts = dict.fromkeys(CATEGORY_LABELS, 0)
    for batch in batches:
        if not show_all and batch["date"] != selected_date:
            continue
        items = []
        for source_item in batch["items"]:
            if not _matches(source_item, query):
                continue
            category_counts[source_item["category"]] += 1
            if category and source_item["category"] != category:
                continue
            item = dict(source_item)
            item["no"] = item["id"].rsplit("-", 1)[-1]
            item["adopted_idea"] = adopted.get(item["daily_tag"])
            adopted_count += bool(item["adopted_idea"])
            items.append(item)
        if items or not (query or category):
            batch_day = date.fromisoformat(batch["date"])
            groups.append({**batch, "items": items, "day": batch_day, "weekday": WEEKDAYS[batch_day.weekday()]})
            total += len(items)

    # 날짜를 옮겨도 검색어·분류는 유지한다.
    keep = urlencode({key: value for key, value in (("q", query), ("category", category)) if value})
    return render(
        request,
        "daily_ideas/list.html",
        {
            "page_title": "일일 아이디어",
            "groups": groups,
            "selected_date": selected_date,
            "selected_day": None if show_all else anchor,
            "selected_weekday": "" if show_all else WEEKDAYS[anchor.weekday()],
            "has_research": show_all or selected_date in counts,
            "show_all": show_all,
            "calendar": _calendar(anchor, selected_date, counts, today),
            "keep": f"&{keep}" if keep else "",
            "keep_q": f"&{urlencode({'q': query})}" if query else "",
            "q": query,
            "category": category,
            "categories": [(value, label, category_counts[value]) for value, label in CATEGORY_LABELS.items()],
            "category_total": sum(category_counts.values()),
            "total": total,
            "adopted_count": adopted_count,
            "is_filtered": bool(query or category),
        },
    )


def _next_code() -> str:
    highest = 0
    for code in Idea.all_objects.values_list("code", flat=True):
        match = re.fullmatch(r"C(\d+)", code)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"C{highest + 1:02d}"


@require_POST
def adopt(request, item_id: str):
    item = find_item(item_id)
    from apps.core.trash import hidden_keys
    if item is None or item_id in hidden_keys("daily"):
        raise Http404("일일 아이디어를 찾을 수 없습니다.")

    existing = next(
        (
            idea
            for idea in Idea.objects.filter(tags__contains=item["daily_tag"])
            if item["daily_tag"] in idea.tag_list
        ),
        None,
    )
    # 담아도 화면은 그대로 둔다 (사용자 요청 2026-10-14): 제자리 요청이면 JSON, 아니면 보던 목록으로 돌아간다.
    back_to = f"{reverse('daily_ideas:list')}?date={item['date']}#idea-{item['id']}"
    if existing:
        message = f"{existing.code}에 이미 담긴 아이디어입니다."
        if request.headers.get("X-Requested-With") != "fetch":
            messages.info(request, message)
        return answer(request, back_to, code=existing.code, url=existing.get_absolute_url(), message=message)

    source_lines = "\n".join(f"- {source['label']}: {source['url']}" for source in item["sources"])
    evidence = f"{item['evidence']}\n\n원문 근거\n{source_lines}"
    notes = f"[daily-id:{item['id']}]\n조사일: {item['date']}\n첫 검증: {item['first_test']}"
    # 추적용 태그를 앞에 둬서 긴 주제 태그가 잘려도 중복 담기를 막는다.
    tags = ",".join([item["daily_tag"], *item.get("tags", [])])

    with transaction.atomic():
        idea = Idea.objects.create(
            code=_next_code(),
            title=item["title"],
            category=CATEGORY_TO_IDEA[item["category"]],
            status=Idea.Status.CANDIDATE,
            priority=3,
            customer=item["audience"],
            pain=item["problem"],
            money_flow=item["money_flow"],
            evidence=evidence,
            min_product=item["min_product"],
            channel=item["channel"],
            risk=item["risk"],
            judgement=item["decision"],
            notes=notes,
            source_doc=item["source_doc"],
            tags=tags[:200],
        )

    message = f"{idea.code}로 내 아이디어에 담았습니다."
    if request.headers.get("X-Requested-With") != "fetch":
        messages.success(request, message)
    return answer(request, back_to, code=idea.code, url=idea.get_absolute_url(), message=message)


# ---------------------------------------------------------------------------
# 아이디어 검색 표준
# ---------------------------------------------------------------------------
def standard(request):
    """검색 표준 쓰기. 저장할 때마다 새 버전. ?v=N 은 그 버전을 불러와 보여 준다(저장하면 새 버전)."""
    request.nav_key = "daily_standard"
    latest = SearchStandard.latest()
    history = list(SearchStandard.objects.all()[:30])

    if request.method == "POST":
        form = StandardForm(request.POST)
        if form.is_valid():
            values = {name: form.cleaned_data[name] for name in STANDARD_FIELDS}
            if latest and latest.same_as(values):
                messages.info(request, f"바뀐 내용이 없어 v{latest.version} 을 그대로 둡니다.")
                return redirect("daily_ideas:standard")
            item = form.save(commit=False)
            item.version = (SearchStandard.all_objects.order_by("-version").values_list("version", flat=True).first() or 0) + 1
            item.save()
            messages.success(request, f"검색 표준 v{item.version} 을 저장했습니다. 오른쪽 요청문을 복사해 조사를 맡기세요.")
            return redirect("daily_ideas:standard")
        viewing = None
    else:
        viewing = None
        if request.GET.get("v", "").isdigit():
            viewing = SearchStandard.objects.filter(version=int(request.GET["v"])).first()
        source = viewing or latest
        initial = {**(source.values() if source else standard_defaults())}
        form = StandardForm(initial=initial)

    for_date = _parse_date(request.GET.get("for", "")) or timezone.localdate()
    current = viewing or latest
    return render(
        request,
        "daily_ideas/standard.html",
        {
            "page_title": "아이디어 검색 표준",
            "form": form,
            "sections": [form[name] for name in STANDARD_FIELDS],
            "latest": latest,
            "viewing": viewing if viewing and latest and viewing.version != latest.version else None,
            "history": history,
            "for_date": for_date.isoformat(),
            "request_text": standard_request(current, for_date.isoformat()) if current else "",
            "current": current,
        },
    )


def standard_markdown(request):
    """검색 표준 Markdown 내려받기 (?v=N 이면 그 버전)."""
    item = None
    if request.GET.get("v", "").isdigit():
        item = SearchStandard.objects.filter(version=int(request.GET["v"])).first()
    item = item or SearchStandard.latest()
    if item is None:
        raise Http404("아직 저장한 검색 표준이 없습니다.")
    body = standard_to_markdown(item.values(), title=f"아이디어 검색 표준 v{item.version} ({item.saved_label})")
    response = HttpResponse(body, content_type="text/markdown; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="idea-search-standard-v{item.version}.md"'
    return response
