"""블로그·카페 › 모니터링 (2026-10-22 사용자: 전처럼 말고 쓸모 있는 것만). 2026-10-23 사용자: 맨 위 메뉴, 네 칸 대시보드 —
발행 실적 · 일일루틴 글쓰기 / 그날 발행 · 오늘의 글 (dash.py). 아래는 그 가운데 발행 실적(한 주) 표.

- 사이트 × 요일 한 주: 그날 발행한 글 수 / 하루 편수. 위 달력 띠는 일일루틴처럼 ← → 로 한 주씩, 날짜를 고르면 그 주.
  칸을 누르면 왼쪽 아래가 그날(그 사이트)의 발행 예정 · 발행한 글.
- 센 글: RSS 로 읽은 글 + 글 관리에서 발행 완료한 글(넣은 곳 · 사이트만 정한 글) + 예전 발행 계획. 같은 제목은 한 번만.
- 발행 확인: 서버는 티스토리·네이버에 못 나가서(feeds 머리말) PC 가 RSS 를 읽어 api_feeds 로 보낸다
  ('발행 확인' 버튼 → jbroutine:feeds, 일일루틴 '전체 실행' 때도 같이). 읽은 글과 제목이 같은 미발행 글은 발행 완료로 바뀐다.
- 통계현황 (stats, 2026-10-23 사용자): 사이트별 방문자 · 공감 · 댓글 추이. 같은 PC 실행에서 같이 읽는다 (stats.py).
"""
import hmac
import json
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_not_required
from django.db.models import Max
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.blog_rules.models import Blog
from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting

from . import dash, feeds, stats
from .models import FeedEntry, FeedState, Plan

DAY_NAMES = "월화수목금토일"
CHECK_HEAD = "# 발행 확인"  # apps/routines/local_run.FEEDS_HEAD


def _day(request):
    try:
        return date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        return timezone.localdate()


def published(blogs, start, end):
    """(블로그 pk, 날짜) → {제목 key: (제목, 주소)}. RSS 글을 먼저 세고, 글 관리의 발행 완료 · 예전 계획은
    같은 사이트에 같은 제목의 RSS 글이 없을 때만 (날짜가 하루 어긋나도 두 번 세지 않게)."""
    from apps.blog_types.models import Placement
    from apps.naver_writing.models import Post as NaverPost
    from apps.writing.models import Post

    ids = {b.pk: b for b in blogs}
    out, seen = {}, set()
    lo = timezone.make_aware(datetime.combine(start - timedelta(days=1), datetime.min.time()))
    hi = timezone.make_aware(datetime.combine(end + timedelta(days=2), datetime.min.time()))
    for e in FeedEntry.objects.filter(blog__in=blogs, published_at__range=(lo, hi)):
        key = feeds._norm(e.title)
        seen.add((e.blog_id, key))
        day = timezone.localtime(e.published_at).date()
        if start <= day <= end:
            out.setdefault((e.blog_id, day), {})[key] = (e.title, e.url)

    def add(blog_id, day, title, url=""):
        key = feeds._norm(title)
        if day and start <= day <= end and (blog_id, key) not in seen:
            seen.add((blog_id, key))
            out.setdefault((blog_id, day), {})[key] = (title, url)

    for pl in (Placement.objects.filter(site_category__blog__in=blogs, status=Placement.Status.PUBLISHED)
               .select_related("site_category", "tistory_post", "naver_post")):
        post = pl.post
        if post is not None:
            add(pl.site_category.blog_id, post.published_on, pl.converted_title or post.title)
    names = {b.name: b.pk for b in blogs}
    for model in (Post, NaverPost):
        for post in model.objects.filter(publish_status=model.Publish.DONE, published_on__range=(start, end),
                                         target__in=names, placements__isnull=True):
            add(names[post.target], post.published_on, post.title)
    for p in Plan.objects.filter(blog__in=blogs, status=Plan.Status.PUBLISHED, published_on__range=(start, end)):
        add(p.blog_id, p.published_on, p.title, p.url)
    return {k: v for k, v in out.items() if k[0] in ids}


def published_keys(blogs, start, end):
    """(블로그 pk, 날짜) → 발행 글 key 집합 (운영 화면 apps.blog_rules 가 쓴다)."""
    return {k: set(v) for k, v in published(blogs, start, end).items()}


def index(request):
    request.nav_key = "blog_ops"
    today = timezone.localdate()
    sel = _day(request)
    start = sel - timedelta(days=sel.weekday())
    days = [start + timedelta(days=i) for i in range(7)]
    blogs = list(Blog.objects.filter(status=Blog.Status.ACTIVE))
    done = published(blogs, start, days[-1])
    try:
        site = int(request.GET.get("site", ""))
    except ValueError:
        site = None
    rows = []
    for b in blogs:
        cells = [{"day": d, "count": len(done.get((b.pk, d), ())), "target": b.daily, "future": d > today,
                  "today": d == today, "on": d == sel and site == b.pk} for d in days]
        rows.append({"blog": b, "cells": cells, "sum": sum(c["count"] for c in cells), "target": b.daily * 7})
    totals = [sum(r["cells"][i]["count"] for r in rows) for i in range(7)]
    strip = [{"day": d, "name": DAY_NAMES[i], "count": totals[i], "on": d == sel, "today": d == today,
              "future": d > today, "weekend": i >= 5} for i, d in enumerate(days)]
    states = {s.blog_id: s for s in FeedState.objects.filter(blog__in=blogs)}
    for r in rows:
        r["state"] = states.get(r["blog"].pk)
    day_groups = dash.day_posts(blogs, sel, done, site)
    week_no = start.isocalendar()[1]
    return render(request, "blog_ops/index.html", {
        "page_title": "모니터링", "today": today,
        "sel": sel, "site": site, "start": start, "end": days[-1], "week_no": week_no,
        "is_this_week": start <= today <= days[-1],
        "prev": (sel - timedelta(days=7)).isoformat(), "next": (sel + timedelta(days=7)).isoformat(),
        "days": [(d, DAY_NAMES[i], d == today) for i, d in enumerate(days)],
        "strip": strip, "rows": rows,
        "week_sum": sum(totals), "week_target": sum(r["target"] for r in rows),
        "picked_site": next((b for b in blogs if b.pk == site), None),
        "day_groups": day_groups,  # 왼쪽 아래: 그날 발행 예정 · 발행
        "ready_ids": dash.ready_ids(day_groups),  # 그 칸의 '전체 변환'
        "new_groups": dash.new_posts(blogs, today),  # 오른쪽 아래: 오늘의 글
        "wr": dash.writing(request, today),  # 오른쪽 위: 일일루틴 글쓰기
        "checked_at": FeedState.objects.aggregate(m=Max("checked_at"))["m"],
    })


def _token():
    return AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)


def check_text(request):
    """PC 가 읽을 것: 보낼 주소(토큰 포함) + 운영 중인 사이트의 RSS 주소. 보고 토큰이 없으면 ""."""
    token = _token()
    if not token:
        return ""
    sites = [{"blog": b.pk, "name": b.name, "url": feeds.feed_url(b)}
             for b in Blog.objects.filter(status=Blog.Status.ACTIVE)]
    targets = [stats.target(b) for b in Blog.objects.filter(status=Blog.Status.ACTIVE)]
    payload = {"api": request.build_absolute_uri(reverse("blog_ops:api_feeds")), "token": token, "feeds": sites,
               "stats": targets}
    return f"{CHECK_HEAD}\n{json.dumps(payload, ensure_ascii=False)}\n"


@require_POST
def check(request):
    """'발행 확인' 버튼: PC 에 넘길 안내(JSON). 화면이 클립보드에 넣고 jbroutine:feeds 링크를 연다."""
    text = check_text(request)
    if not text:
        return JsonResponse({"error": "보고 토큰이 없습니다. 설정에서 보고 토큰을 만드세요."}, status=400)
    now = timezone.localtime()
    return JsonResponse({"prompt": text, "key": f"fd-{now:%H%M%S}", "day": now.date().isoformat()})


def status(request):
    """마지막 확인 시각 (화면이 PC 확인이 끝났는지 볼 때)."""
    m = FeedState.objects.aggregate(m=Max("checked_at"))["m"]
    return JsonResponse({"checked_at": m.isoformat() if m else ""})


@csrf_exempt
@login_not_required
@require_POST
def api_feeds(request):
    """PC 가 읽은 RSS: {"token", "results": [{"blog", "ok", "message", "items": [[제목, 주소, ISO 시각]]}]}."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return HttpResponseBadRequest("json")
    token = _token()
    if not token or not hmac.compare_digest(str(data.get("token", "")), token):
        return HttpResponseForbidden("token")
    blogs = {b.pk: b for b in Blog.objects.all()}
    out = []
    for r in data.get("results") or []:
        blog = blogs.get(r.get("blog"))
        if blog is None:
            continue
        items = []
        for row in r.get("items") or []:
            try:
                title, url, when = str(row[0]).strip(), str(row[1]).strip(), datetime.fromisoformat(row[2])
            except (TypeError, ValueError, IndexError):
                continue
            if title and url.startswith("http"):
                items.append((title, url, when if when.tzinfo else timezone.make_aware(when)))
        state = feeds.record(blog, bool(r.get("ok")), str(r.get("message", "")), items, where="PC")
        out.append({"blog": blog.name, "ok": state.ok, "message": state.message})
    for r in data.get("stats") or []:  # 통계 (방문자 · 공감 · 댓글)
        blog = blogs.get(r.get("blog"))
        if blog is not None and isinstance(r, dict):
            state = stats.record(blog, r)
            out.append({"blog": f"{blog.name} 통계", "ok": state.stat_ok, "message": state.stat_message})
    by_host = stats.ga4_blogs(blogs.values())
    for r in data.get("ga4") or []:  # GA4 (2026-10-27): 날짜별 방문자·조회 · 많이 본 글 · 유입
        blog = by_host.get(str(r.get("host", ""))) if isinstance(r, dict) else None
        if blog is not None:
            out.append({"blog": f"{blog.name} GA4", "ok": True, "message": stats.record_ga4(blog, r)})
    return JsonResponse({"results": out}, json_dumps_params={"ensure_ascii": False})


PERIODS = [(7, "7일"), (30, "30일"), (90, "90일")]


def stats_page(request):
    """통계현황 (?days=7|30|90 &site=<사이트>): 사이트 칸 · 하루 방문자 · 많이 본 글 · 어디서 왔나 (2026-10-27 사용자: 쉽게 싹 갈아엎기).
    기본은 7일, 사이트 칸을 누르면 그 사이트만."""
    request.nav_key = "blog_stats"
    today = timezone.localdate()
    try:
        n = int(request.GET.get("days", 7))
    except ValueError:
        n = 7
    n = n if n in dict(PERIODS) else 7
    days = [today - timedelta(days=n - 1 - i) for i in range(n)]
    order = list(Blog.objects.values_list("pk", flat=True))  # 색은 사이트 순서로 고정
    blogs = list(Blog.objects.filter(status=Blog.Status.ACTIVE))
    selected = next((b for b in blogs if str(b.pk) == request.GET.get("site", "")), None)
    return render(request, "blog_ops/stats.html", {
        "page_title": "통계현황", **stats.page_data(blogs, order, days, today, selected), "days": days, "n": n, "periods": PERIODS,
        "selected": selected, "today": today, "checked_at": FeedState.objects.aggregate(m=Max("stat_checked_at"))["m"],
    })
