"""커스텀 글쓰기: 주제가 정해진 글쓰기 (2026-10-21 사용자). 일일루틴과 따로, 주 단위로 본다.

- 고정 주제(FixedTopic) 한 줄: 주제 · 지침 · 최근 몇 주 발행 여부(점) · 실행. 점을 누르면 그 주 발행/미발행이 바뀐다.
- '실행': 글쓰기 루틴의 추가 실행처럼 PC 터미널 claude 에게 이 주제 한 편을 맡긴다 (글쓰기 프롬프트 md 를 그대로 따른다).
- 왼쪽 자유 글쓰기 (2026-10-21 사용자): 쓰고 싶은 걸 자유롭게 적고 '글쓰기' → 추가 실행의 코멘트와 같은 길 (views.extra mode=comment).
- 일일루틴 화면의 글쓰기 줄을 누르면 고정 주제가 그 아래로 펼쳐지고, 거기서도 추가·실행·발행 표시를 한다.
"""
from datetime import timedelta

from django.contrib import messages
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog_types import sites

from .models import FixedTopic, Routine, TopicWeek, week_start

WRITING_KEY = "writing"
DOT_W = 34  # 주 한 칸 폭 (점 · 머리글 날짜가 같은 폭, app.css .tp-dots)


def weeks(today, n):
    """최근 n 주의 월요일 (오래된 주 → 이번 주)"""
    this = week_start(today)
    return [this - timedelta(weeks=i) for i in range(n - 1, -1, -1)]


def topic_text(topic, today):
    """추가 실행의 '이번에 할 것' 자리에 들어갈 내용"""
    mon = week_start(today)
    lines = [
        f"고정 주제 (커스텀 글쓰기): {topic.name} — {topic.per_week}편.",
        f"- 이번 주({mon:%m-%d} ~ {mon + timedelta(days=6):%m-%d})에 쓰는 글이다. 다루는 기간·지역은 아래 지침을 따르고"
        " (예: 공모주는 앞으로 한 달·분기), 지침에 없으면 이번 주 기준. 일정·숫자는 공식 출처에서 오늘 다시 확인한다.",
        f"- 사이트: {topic.site or '주제에 맞는 사이트를 고른다'}",
        "- 같은 주제의 지난 원고(원고 폴더의 `고정주제:` 줄)를 먼저 보고, 겹치는 건 바뀐 것만 짚고 새 내용 위주로 쓴다.",
        f"- 글감부터 본다 (2026-10-22 사용자): 오늘({today:%Y-%m-%d}) 기준으로 새로 쓸 게 없으면 원고를 만들지 않는다 — 폴더·원고.md 없이"
        " 진행 보고에 '글감 없음 · 이유 한 줄'만 남기고 끝낸다. 억지로 채운 글은 품질만 떨어뜨린다.",
        "- 날짜가 지난 것은 쓰지 않는다: 접수·마감·청약·상장·발표일이 오늘 이전에 끝난 항목은 빼고, 쓰기 직전에 항목마다 날짜를 오늘과 다시 대조한다."
        " 남는 게 지난 원고와 같은 항목뿐이고 바뀐 게 없으면 글감 없음이다.",
        f"- 원고 제작 정보 맨 위 `사이트:` · `분류:` 줄 아래에 `고정주제: {topic.name}` 줄을 넣는다.",
        "- 분류는 '글 분류 전체'에서 주제에 맞는 것을 고른다.",
    ]
    if topic.note.strip():
        lines += ["", "이 주제의 지침 (사용자):", topic.note.strip()]
    return "\n".join(lines)


def all_text(topics, today):
    """전체 실행 (2026-10-21 사용자): 모든 고정 주제를 한 터미널에서 차례로."""
    lines = [f"고정 주제 전체 실행 (커스텀 글쓰기): 아래 {len(topics)}개 주제를 순서대로 하나씩 끝까지 쓴다. "
             "주제마다 원고를 따로 만들고(주당 편수만큼), 한 주제가 끝나면 진행 보고 후 다음 주제로 간다. "
             "글감 없는 주제는 원고 없이 '글감 없음'만 보고하고 다음 주제로 간다."]
    for n, t in enumerate(topics, start=1):
        lines += ["", f"#### {n}. {t.name}", topic_text(t, today)]
    return "\n".join(lines)


def all_prompt_for(request, topics, day):
    from .views import launcher, report_url
    writing = Routine.objects.filter(key=WRITING_KEY).first()
    if writing is None or not topics:
        return ""
    return launcher(writing, day, report=report_url(request, writing, day), extra=all_text(topics, day), tree=True)


def prompt_for(request, topic, day):
    """PC 터미널 claude 에게 줄 안내문. 글쓰기 루틴이 없으면 빈 값 (실행 버튼을 숨긴다)."""
    from .views import launcher, report_url
    writing = Routine.objects.filter(key=WRITING_KEY).first()
    if writing is None:
        return ""
    return launcher(writing, day, report=report_url(request, writing, day), extra=topic_text(topic, day), tree=True)


def rows(request, n, today=None):
    """고정 주제마다 .cells = [(주 월요일, 발행, 이번 주인지)], .prompt"""
    today = today or timezone.localdate()
    ws = weeks(today, n)
    topics = list(FixedTopic.objects.all())
    done = set(TopicWeek.objects.filter(topic__in=topics, week__in=ws, published=True).values_list("topic_id", "week"))
    for t in topics:
        t.cells = [(w, (t.pk, w) in done, w == ws[-1]) for w in ws]
        t.week_done = (t.pk, ws[-1]) in done  # 이번 주 발행
        t.prompt = prompt_for(request, t, today)
    return topics, ws


def _back(request, fallback="routines:topics"):
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else fallback)


def page(request):
    request.nav_key = "routine_topics"
    today = timezone.localdate()
    topics, ws = rows(request, 8, today)
    return render(request, "routines/topics.html", {
        "page_title": "커스텀 글쓰기", "topics": topics, "weeks": ws, "today": today,
        "this_week": ws[-1], "done_this_week": sum(1 for t in topics if t.cells[-1][1]),
        "week_col": len(ws) * DOT_W + 32, "site_names": sites.names(),
        "writing": Routine.objects.filter(key=WRITING_KEY).first(),
        "all_prompt": all_prompt_for(request, topics, today),  # 왼쪽 자유 글쓰기 = 글쓰기 루틴의 추가 실행(코멘트)
    })


@require_POST
def add(request):
    name = " ".join(request.POST.get("name", "").split())[:60]
    if not name:
        messages.warning(request, "주제 이름을 적으세요.")
        return _back(request)
    order = (FixedTopic.all_objects.aggregate(m=Max("order"))["m"] or 0) + 1
    FixedTopic.objects.create(name=name, order=order)
    messages.success(request, f"고정 주제 '{name}'을(를) 추가했습니다. 지침은 커스텀 글쓰기에서 적으세요.")
    return _back(request)


@require_POST
def save(request, pk):
    topic = get_object_or_404(FixedTopic, pk=pk)
    name = " ".join(request.POST.get("name", "").split())[:60]
    if name:
        topic.name = name
    topic.site = request.POST.get("site", "").strip()[:60]
    topic.note = request.POST.get("note", "").strip()
    raw = request.POST.get("per_week", "")
    if raw.isdigit() and 1 <= int(raw) <= 7:
        topic.per_week = int(raw)
    topic.save()
    messages.success(request, f"'{topic.name}'을(를) 저장했습니다.")
    return _back(request)


@require_POST
def week(request, pk):
    """그 주 발행 표시를 뒤집는다. week=YYYY-MM-DD (어느 날이든 그 주 월요일로)."""
    topic = get_object_or_404(FixedTopic, pk=pk)
    try:
        mon = week_start(timezone.datetime.fromisoformat(request.POST.get("week", "")).date())
    except ValueError:
        return _back(request)
    tw, _ = TopicWeek.objects.get_or_create(topic=topic, week=mon)
    tw.published = not tw.published
    tw.save(update_fields=["published", "updated_at"])
    return _back(request)


@require_POST
def delete(request, pk):
    topic = get_object_or_404(FixedTopic, pk=pk)
    topic.delete()  # 휴지통으로
    messages.success(request, f"'{topic.name}'을(를) 휴지통으로 옮겼습니다.")
    return _back(request)
