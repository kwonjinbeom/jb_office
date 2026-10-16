"""블로그·카페 › 운영: 이번 주 발행 현황(블로그 × 요일), 숫자 네 개, 발행 계획(할 일)."""
import re
from datetime import date, timedelta

from django import forms
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog_rules.models import Blog

from . import feeds
from .models import FeedEntry, FeedState, Plan

DAY_NAMES = "월화수목금토일"


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ["planned_on", "blog", "title", "status", "url", "published_on", "memo"]
        widgets = {
            "planned_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "published_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


def _nav(request):
    request.nav_key = "blog_ops"


def _week_start(request):
    try:
        d = date.fromisoformat(request.GET.get("week", ""))
    except ValueError:
        d = timezone.localdate()
    return d - timedelta(days=d.weekday())


def _key(url, title):
    return url or re.sub(r"\s+", "", title or "")


def _published(blogs, start, end):
    """(블로그 pk, 날짜) → 발행 글 key 집합. 계획의 '발행' 기록과 RSS 기록을 합치고 같은 글은 한 번만 센다."""
    out = {}
    for p in Plan.objects.filter(blog__in=blogs, status=Plan.Status.PUBLISHED, published_on__range=(start, end)):
        out.setdefault((p.blog_id, p.published_on), set()).add(_key(p.url, p.title))
    for e in FeedEntry.objects.filter(blog__in=blogs):
        day = timezone.localtime(e.published_at).date()
        if start <= day <= end:
            keys = out.setdefault((e.blog_id, day), set())
            if _key("", e.title) not in keys:  # 계획에 주소 없이 제목만 있던 글과 겹치지 않게
                keys.add(_key(e.url, e.title))
    return out


def index(request):
    _nav(request)
    today = timezone.localdate()
    start = _week_start(request)
    days = [start + timedelta(days=i) for i in range(7)]
    blogs = list(Blog.objects.filter(status=Blog.Status.ACTIVE))
    done = _published(blogs, start, days[-1])
    rows = []
    for b in blogs:
        cells = [{"day": d, "count": len(done.get((b.pk, d), ())), "target": b.daily,
                  "future": d > today, "today": d == today} for d in days]
        rows.append({"blog": b, "cells": cells, "sum": sum(c["count"] for c in cells), "target": b.daily * 7})
    today_target = sum(b.daily for b in blogs)
    today_done = sum(len(done.get((b.pk, today), ())) for b in blogs) if start <= today <= days[-1] else None
    open_plans = Plan.objects.exclude(status=Plan.Status.PUBLISHED)
    plans = Plan.objects.select_related("blog").filter(
        Q(planned_on__range=(start, days[-1])) | Q(planned_on__lt=start, status__in=[
            Plan.Status.DRAFT, Plan.Status.EDIT, Plan.Status.SCHEDULED]))
    states = {s.blog_id: s for s in FeedState.objects.filter(blog__in=blogs)}
    return render(request, "blog_ops/index.html", {
        "page_title": "운영",
        "days": [(d, DAY_NAMES[i], d == today) for i, d in enumerate(days)],
        "rows": rows,
        "week_label": f"{start:%m.%d} – {days[-1]:%m.%d}",
        "prev_week": (start - timedelta(days=7)).isoformat(),
        "next_week": (start + timedelta(days=7)).isoformat(),
        "is_this_week": start <= today <= days[-1],
        "tiles": [
            ("오늘 발행", f"{today_done}/{today_target}" if today_done is not None else "—"),
            ("이번 주 발행", f"{sum(r['sum'] for r in rows)}/{sum(r['target'] for r in rows)}"),
            ("예약", open_plans.filter(status=Plan.Status.SCHEDULED).count()),
            ("손질 대기", open_plans.filter(status__in=[Plan.Status.DRAFT, Plan.Status.EDIT]).count()),
        ],
        "plans": plans,
        "statuses": Plan.Status.choices,
        "all_blogs": Blog.objects.exclude(status=Blog.Status.HOLD),
        "today": today,
        "feeds": [(b, states.get(b.pk)) for b in blogs],
        "week_qs": "" if start <= today <= days[-1] else f"?week={start.isoformat()}",
    })


def _back(request):
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else reverse("blog_ops:index"))


@require_POST
def plan_add(request):
    title = " ".join(request.POST.get("title", "").split())[:200]
    blog = Blog.objects.filter(pk=request.POST.get("blog") or 0).first()
    try:
        planned = date.fromisoformat(request.POST.get("planned_on", ""))
    except ValueError:
        planned = timezone.localdate()
    if not title or blog is None:
        messages.warning(request, "블로그와 제목을 입력하세요.")
    else:
        Plan.objects.create(blog=blog, title=title, planned_on=planned)
    return _back(request)


@require_POST
def plan_status(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    value = request.POST.get("status", "")
    if value in Plan.Status.values:
        plan.status = value
        if value == Plan.Status.PUBLISHED and not plan.published_on:
            plan.published_on = timezone.localdate()
        plan.save()
    return _back(request)


def plan_edit(request, pk):
    _nav(request)
    plan = get_object_or_404(Plan, pk=pk)
    form = PlanForm(request.POST or None, instance=plan)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if saved.status == Plan.Status.PUBLISHED and not saved.published_on:
            saved.published_on = timezone.localdate()
        saved.save()
        messages.success(request, "저장했습니다.")
        return redirect("blog_ops:index")
    return render(request, "blog_ops/form.html", {"page_title": "발행 계획 수정", "form": form, "plan": plan})


def plan_delete(request, pk):
    _nav(request)
    plan = get_object_or_404(Plan, pk=pk)
    if request.method == "POST":
        plan.delete()  # 휴지통으로
        messages.success(request, "휴지통으로 옮겼습니다.")
        return redirect("blog_ops:index")
    return render(request, "blog_ops/confirm_delete.html", {"page_title": "삭제", "plan": plan})


@require_POST
def sync(request):
    results = [feeds.sync(b) for b in Blog.objects.filter(status=Blog.Status.ACTIVE)]
    ok = sum(1 for s in results if s.ok)
    if ok:
        messages.success(request, f"RSS {ok}곳을 읽었습니다.")
    if ok < len(results):
        messages.warning(request, f"RSS {len(results) - ok}곳은 읽지 못했습니다. 아래 RSS 칸을 보세요.")
    return _back(request)
