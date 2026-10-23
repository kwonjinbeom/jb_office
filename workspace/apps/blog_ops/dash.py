"""모니터링 대시보드 (2026-10-23 사용자: 운영 · 파이프라인 관리를 한 화면에서, 큼지막하게).

- 숫자 칸: 오늘 발행 · 이번 주 발행 · 발행 대기(며칠치) · 검토 대기 · 일일루틴 오늘 · 발행 확인(RSS)
- 확인할 것: 손이 가야 하는 것만 한 줄씩, 누르면 그 화면으로 (오늘 남은 편수 · 예정일 지남 · 발행 대기 부족 ·
  다음 7일 빈 날 · 예정일 미정 · 사이트 미정 · 변환 전 · RSS 실패 · 루틴 실패 · 며칠째 발행 없음)
- 파이프라인: 사이트마다 임시글 → 검토글 → 발행예정(미발행) 수, 예정일 미정, 며칠치, 다음 7일 예정 칸
- 일일루틴: 루틴마다 지난 7일 결과 수(일일루틴 화면과 같은 셈)와 오늘 실행 상태

글의 사이트: 임시글·검토글은 고른 사이트(target). 발행예정글은 넣은 곳(미발행)의 사이트, 넣은 곳이 없으면 고른 사이트.
"""
from collections import Counter
from datetime import timedelta
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone

LOW_DAYS = 2  # 발행 대기가 이보다 적은 날치면 '부족'
QUIET_DAYS = 3  # 이만큼 발행이 없으면 '며칠째 발행 없음'


def _url(name, **query):
    q = urlencode({k: v for k, v in query.items() if v})
    return reverse(name) + (f"?{q}" if q else "")


def pipeline(blogs, today):
    """사이트별 단계 수와 확인할 것의 재료. (rows, extra)"""
    from apps.blog_types.classify import WRITERS, post_model
    from apps.blog_types.models import Placement

    names = {b.name: b for b in blogs}
    stage = Counter()  # (사이트 이름, 단계) → 수
    days = Counter()  # (사이트 이름, 예정일) → 수
    overdue, undated, no_site = Counter(), Counter(), 0
    for w in WRITERS:
        model = post_model(w)
        for post in (model.objects.exclude(publish_status=model.Publish.DONE)
                     .prefetch_related("placements__site_category__blog")):
            if post.stage != "post":
                if post.target:
                    stage[(post.target, post.stage)] += 1
                elif post.stage == "review":
                    no_site += 1
                continue
            where = {pl.site_category.blog.name for pl in post.placements.all() if pl.status == Placement.Status.UNSAVED}
            where = where or ({post.target} if post.target else set())
            if not where:
                no_site += 1
            for name in where:
                stage[(name, "post")] += 1
                if post.planned_on is None:
                    undated[name] += 1
                elif post.planned_on < today:
                    overdue[name] += 1
                else:
                    days[(name, post.planned_on)] += 1
    convert = Counter(Placement.objects.filter(status=Placement.Status.UNSAVED, site_category__blog__in=blogs,
                                               convert_status__in=[Placement.Convert.NONE, Placement.Convert.REQUESTED])
                      .values_list("site_category__blog__name", flat=True))
    ahead = [today + timedelta(days=i) for i in range(7)]
    rows = []
    for b in blogs:
        post = stage[(b.name, "post")]
        cells = [{"day": d, "count": days[(b.name, d)], "gap": days[(b.name, d)] < b.daily} for d in ahead]
        rows.append({
            "blog": b, "temp": stage[(b.name, "temp")], "review": stage[(b.name, "review")], "post": post,
            "undated": undated[b.name], "overdue": overdue[b.name], "convert": convert[b.name],
            "stock": round(post / b.daily, 1) if b.daily else None, "cells": cells,
            "gaps": sum(1 for c in cells if c["gap"]),
            "links": {k: _url("posts:view", stage=k, site=b.name) for k in ("temp", "review")}
                     | {"post": _url("posts:planned", site=b.name)},
        })
    return rows, {"ahead": ahead, "no_site": no_site, "names": names}


def routines(today):
    """루틴마다 지난 7일 결과 수(고친 값이 있으면 그 값)와 오늘 실행."""
    from apps.routines.models import Routine, RoutineDay, RoutineRun
    from apps.routines.views import _auto

    lo = today - timedelta(days=6)
    week = [lo + timedelta(days=i) for i in range(7)]
    fixed = {(r.routine_id, r.day): r.done for r in RoutineDay.objects.filter(day__range=(lo, today))}
    runs = {}
    for run in RoutineRun.objects.filter(day=today).select_related("routine"):  # 최근 보고가 앞 (ordering)
        runs.setdefault(run.routine_id, run)
    out = []
    for r in Routine.objects.all():
        auto = _auto(r.key, lo, today)
        cells = [{"day": d, "count": fixed.get((r.pk, d), auto[d]), "today": d == today} for d in week]
        for c in cells:
            c["met"] = bool(r.daily) and c["count"] >= r.daily
        out.append({"routine": r, "cells": cells, "run": runs.get(r.pk), "today": cells[-1]})
    return out, week


def _ago(day, today):
    n = (today - day).days
    return "오늘" if n == 0 else "어제" if n == 1 else f"{n}일 전"


def attention(rows, extra, today_done, last_day, states, routine_rows, today):
    """확인할 것: (단계 'bad'|'warn'|'', 글, 덧말, 주소). 급한 것이 위."""
    items = []
    planned = reverse("posts:planned")
    for r in rows:
        b = r["blog"]
        if r["overdue"]:
            items.append(("bad", f"{b.name} · 예정일 지난 글 {r['overdue']}편", "발행하거나 날짜를 옮기기", r["links"]["post"]))
    for r in rows:
        b, left = r["blog"], r["blog"].daily - today_done.get(r["blog"].pk, 0)
        if left > 0:
            items.append(("warn", f"{b.name} · 오늘 {left}편 더", f"하루 {b.daily}편", _url("posts:planned", site=b.name)))
    for pk, s in states.items():
        if not s.ok:
            items.append(("bad", f"{extra['names_by_pk'][pk]} · RSS 읽기 실패", s.message[:40], ""))
    for x in routine_rows:
        run = x["run"]
        if run and run.status in ("failed", "blocked"):
            items.append(("bad", f"{x['routine'].name} 루틴 {run.get_status_display()}", run.step[:40], reverse("routines:index")))
    for r in rows:
        b = r["blog"]
        if r["stock"] is not None and r["stock"] < LOW_DAYS:
            items.append(("warn", f"{b.name} · 발행 대기 {r['post']}편 ({r['stock']:g}일치)", "검토글을 발행예정으로", r["links"]["review"]))
        elif r["gaps"]:
            items.append(("warn", f"{b.name} · 다음 7일 중 {r['gaps']}일 예정 모자람", "발행 예정일 채우기", r["links"]["post"]))
    for r in rows:
        b = r["blog"]
        if r["undated"]:
            items.append(("", f"{b.name} · 예정일 미정 {r['undated']}편", "날짜 정하기", r["links"]["post"]))
        if r["convert"]:
            items.append(("", f"{b.name} · 변환 전 {r['convert']}편", "사이트별 템플릿에서 변환", reverse("site_templates:index")))
        last = last_day.get(b.pk)
        if b.daily and (last is None or (today - last).days >= QUIET_DAYS):
            items.append(("", f"{b.name} · {'30일 넘게' if last is None else str((today - last).days) + '일째'} 발행 없음", "", b.address))
    if extra["no_site"]:
        items.append(("", f"사이트 미정 {extra['no_site']}편", "검토글·발행예정글에서 사이트 고르기", _url("posts:view", stage="review")))
    rank = {"bad": 0, "warn": 1, "": 2}
    return sorted(items, key=lambda i: rank[i[0]])


def build(blogs, today, published, states):
    """대시보드 전체. published = views.published (돌아 들어가지 않게 넘겨 받는다)."""
    rows, extra = pipeline(blogs, today)
    extra["names_by_pk"] = {b.pk: b.name for b in blogs}
    recent = published(blogs, today - timedelta(days=29), today)
    today_done = {b.pk: len(recent.get((b.pk, today), ())) for b in blogs}
    last_day = {}
    for (pk, d) in recent:
        if d > last_day.get(pk, d - timedelta(days=1)):
            last_day[pk] = d
    for r in rows:
        r["today"] = today_done[r["blog"].pk]
        r["last"] = last_day.get(r["blog"].pk)
        r["last_label"] = _ago(r["last"], today) if r["last"] else "30일 넘게"
    routine_rows, routine_week = routines(today)
    week_start = today - timedelta(days=today.weekday())
    week_done = sum(len(v) for (pk, d), v in recent.items() if d >= week_start)
    daily = sum(b.daily for b in blogs)
    waiting = sum(r["post"] for r in rows)
    with_goal = [x for x in routine_rows if x["routine"].daily]
    open_run = next((x["run"] for x in routine_rows if x["run"] and x["run"].is_open), None)
    bad_feeds = sum(1 for s in states.values() if not s.ok)
    kpis = {
        "today": (sum(today_done.values()), daily, sum(max(0, b.daily - today_done[b.pk]) for b in blogs)),
        "week": (week_done, daily * 7, round(week_done * 100 / (daily * 7)) if daily else 0),
        "waiting": (waiting, round(waiting / daily, 1) if daily else 0),
        "review": (sum(r["review"] for r in rows), sum(r["temp"] for r in rows)),
        "routines": (sum(1 for x in with_goal if x["today"]["met"]), len(with_goal), open_run),
        "feeds_bad": bad_feeds,
    }
    items = attention(rows, extra, today_done, last_day, states, routine_rows, today)
    names = "월화수목금토일"
    return {"pipe": rows, "ahead": [(d, names[d.weekday()]) for d in extra["ahead"]], "kpis": kpis, "items": items,
            "routine_rows": routine_rows, "routine_week": [(d, names[d.weekday()]) for d in routine_week]}
