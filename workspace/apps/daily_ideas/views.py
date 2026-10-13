from __future__ import annotations

import re

from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.ideas.models import Idea

from .data import CATEGORY_LABELS, find_item, load_batches


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


def daily_list(request):
    batches = load_batches()
    available_dates = [batch["date"] for batch in batches]
    selected_date = request.GET.get("date", "")
    if not selected_date:
        selected_date = available_dates[0] if available_dates else "all"
    if selected_date != "all" and selected_date not in available_dates:
        selected_date = available_dates[0] if available_dates else "all"

    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    if category not in CATEGORY_LABELS:
        category = ""

    adopted = {}
    for idea in Idea.objects.filter(tags__contains="daily:").only("id", "title", "tags"):
        for tag in idea.tag_list:
            if tag.startswith("daily:"):
                adopted[tag] = idea

    groups = []
    total = 0
    for batch in batches:
        if selected_date != "all" and batch["date"] != selected_date:
            continue
        items = []
        for source_item in batch["items"]:
            if category and source_item["category"] != category:
                continue
            if not _matches(source_item, query):
                continue
            item = dict(source_item)
            item["adopted_idea"] = adopted.get(item["daily_tag"])
            items.append(item)
        if items or not (query or category):
            groups.append({**batch, "items": items})
            total += len(items)

    return render(
        request,
        "daily_ideas/list.html",
        {
            "page_title": "일일 아이디어",
            "groups": groups,
            "available_dates": available_dates,
            "selected_date": selected_date,
            "q": query,
            "category": category,
            "categories": CATEGORY_LABELS.items(),
            "total": total,
            "is_filtered": bool(query or category or selected_date == "all"),
        },
    )


def _next_code() -> str:
    highest = 0
    for code in Idea.objects.values_list("code", flat=True):
        match = re.fullmatch(r"C(\d+)", code)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"C{highest + 1:02d}"


@require_POST
def adopt(request, item_id: str):
    item = find_item(item_id)
    if item is None:
        raise Http404("일일 아이디어를 찾을 수 없습니다.")

    existing = next(
        (
            idea
            for idea in Idea.objects.filter(tags__contains=item["daily_tag"])
            if item["daily_tag"] in idea.tag_list
        ),
        None,
    )
    if existing:
        messages.info(request, f"{existing.code}에 이미 담긴 아이디어입니다.")
        return redirect(existing)

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

    messages.success(request, f"{idea.code}로 내 아이디어에 담았습니다.")
    return redirect(idea)
