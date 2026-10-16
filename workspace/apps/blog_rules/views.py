"""블로그·카페 › 운영: 사이트마다 한 줄 (컨셉 · 발행 · 임시저장 · 체크). 위쪽 달력 띠로 일별·월별을 고른다.

발행 = 모니터링의 '발행' 계획 + RSS 로 읽은 글 (같은 글은 한 번). 임시저장 = 그 기간 계획 중 아직 발행 안 한 것.
"""
import calendar
from collections import OrderedDict
from datetime import date, timedelta

from django.contrib import messages
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog_ops.models import Plan
from apps.blog_ops.views import published_keys

from .forms import BlogForm, RuleForm
from .models import Blog, Rule

WEEKDAYS = "월화수목금토일"


def _nav(request):
    request.nav_key = "blog_rules"


def _month_end(first):
    return first.replace(day=calendar.monthrange(first.year, first.month)[1])


def _add_months(first, n):
    m = first.year * 12 + first.month - 1 + n
    return date(m // 12, m % 12 + 1, 1)


def _period(request, today):
    """?month=YYYY-MM 이면 월별, 아니면 ?date=YYYY-MM-DD 일별 (없으면 오늘)."""
    try:
        y, m = (int(x) for x in request.GET.get("month", "").split("-"))
        return "month", date(y, m, 1)
    except ValueError:
        pass
    try:
        return "day", date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        return "day", today


def index(request):
    _nav(request)
    today = timezone.localdate()
    mode, sel = _period(request, today)
    blogs = list(Blog.objects.prefetch_related("checks"))
    active = [b for b in blogs if b.status == Blog.Status.ACTIVE]

    if mode == "day":
        start = end = sel
        monday = sel - timedelta(days=sel.weekday())
        strip_from, strip_to = monday, monday + timedelta(days=6)
        days = 1
    else:
        start, end = sel, _month_end(sel)
        strip_from, strip_to = sel.replace(month=1), _month_end(sel.replace(month=12))
        days = end.day
    done = {k: len(v) for k, v in published_keys(blogs, strip_from, strip_to).items()}  # (블로그 pk, 날짜) → 발행 수
    drafts = dict(Plan.objects.filter(blog__in=blogs, planned_on__range=(start, end))
                  .exclude(status=Plan.Status.PUBLISHED).values_list("blog").annotate(n=Count("pk")))

    def published(lo, hi, blog=None):
        return sum(n for (pk, d), n in done.items() if lo <= d <= hi and (blog is None or pk == blog.pk))

    for b in blogs:
        b.on = b.status == Blog.Status.ACTIVE
        b.published = published(start, end, b)
        b.target = b.daily * days if b.on else 0
        b.drafts = drafts.get(b.pk, 0)
        b.meta = " · ".join(x for x in [
            (f"하루 {b.daily}편" + (f" ({b.daily_note})" if b.daily_note else "")) if b.on else b.get_status_display(),
            b.revenue, b.kpi] if x)
    target_day = sum(b.daily for b in active)
    if mode == "day":
        strip = [{"href": f"?date={d}", "top": WEEKDAYS[i], "main": d.day, "count": published(d, d),
                  "title": f"{d} · 발행 {published(d, d)}/{target_day}", "on": d == sel, "today": d == today,
                  "weekend": i >= 5} for i, d in ((i, strip_from + timedelta(days=i)) for i in range(7))]
        nav = {"prev": f"?date={sel - timedelta(days=1)}", "next": f"?date={sel + timedelta(days=1)}",
               "strip_prev": f"?date={sel - timedelta(days=7)}", "strip_next": f"?date={sel + timedelta(days=7)}",
               "strip_label": f"{strip_from.year}년 {strip_from.month}월 한 주"}
    else:
        strip = []
        for m in range(1, 13):
            lo = date(sel.year, m, 1)
            n = published(lo, _month_end(lo))
            strip.append({"href": f"?month={lo:%Y-%m}", "top": f"{lo:%y}년", "main": f"{m}월", "count": n,
                          "title": f"{lo:%Y-%m} · 발행 {n}", "on": m == sel.month,
                          "today": (lo.year, lo.month) == (today.year, today.month), "weekend": False})
        nav = {"prev": f"?month={_add_months(sel, -1):%Y-%m}", "next": f"?month={_add_months(sel, 1):%Y-%m}",
               "strip_prev": f"?month={_add_months(sel, -12):%Y-%m}", "strip_next": f"?month={_add_months(sel, 12):%Y-%m}",
               "strip_label": f"{sel.year}년"}

    accounts = OrderedDict()  # 같은 계정의 하루 편수 합계 (티스토리: 카카오 계정 단위로 합산된다)
    for b in active:
        if b.account:
            accounts.setdefault(b.account, []).append(b)
    return render(request, "blog_rules/index.html", {
        "page_title": "운영",
        "mode": mode,
        "sel": sel,
        "sel_weekday": WEEKDAYS[sel.weekday()],
        "is_today": sel == today if mode == "day" else (sel.year, sel.month) == (today.year, today.month),
        "strip": strip,
        "nav": nav,
        "month_value": f"{sel:%Y-%m}",
        "blogs": blogs,
        "published_total": sum(b.published for b in blogs),
        "target_total": sum(b.target for b in blogs),
        "drafts_total": sum(b.drafts for b in blogs),
        "daily_total": target_day,
        "accounts": [(name, sum(b.daily for b in items)) for name, items in accounts.items() if len(items) > 1],
        "keep": request.get_full_path().partition("?")[2],
    })


def blog_form(request, pk=None):
    _nav(request)
    blog = get_object_or_404(Blog, pk=pk) if pk else None
    form = BlogForm(request.POST or None, instance=blog)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if not blog:
            saved.order = (Blog.objects.aggregate(m=Max("order"))["m"] or 0) + 1
        saved.save()
        messages.success(request, f"'{saved.name}'을(를) 저장했습니다.")
        return redirect("blog_rules:index")
    return render(request, "blog_rules/form.html", {
        "page_title": "블로그 수정" if blog else "새 블로그", "form": form, "obj": blog, "kind": "blog",
    })


def rule_form(request, pk):
    _nav(request)
    rule = get_object_or_404(Rule, pk=pk)
    form = RuleForm(request.POST or None, instance=rule)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "체크를 저장했습니다.")
        return redirect(f"{_index_url()}#site-{rule.blog_id}")
    return render(request, "blog_rules/form.html", {"page_title": "체크 수정", "form": form, "obj": rule, "kind": "rule"})


@require_POST
def rule_add(request):
    """사이트 체크 한 줄 추가 (입력 후 Enter)."""
    blog = Blog.objects.filter(pk=request.POST.get("blog") or 0).first()
    body = " ".join(request.POST.get("body", "").split())[:200]
    if blog is None or not body:
        messages.warning(request, "체크할 내용을 입력하세요.")
        return _back(request)
    order = (Rule.objects.filter(blog=blog).aggregate(m=Max("order"))["m"] or 0) + 1
    Rule.objects.create(blog=blog, body=body, order=order)
    return _back(request, f"#site-{blog.pk}")


def delete(request, kind, pk):
    _nav(request)
    obj = get_object_or_404(Blog if kind == "blog" else Rule, pk=pk)
    if request.method == "POST":
        obj.delete()  # 휴지통으로 (7일 동안 복원 가능)
        messages.success(request, "휴지통으로 옮겼습니다.")
        return redirect("blog_rules:index")
    return render(request, "blog_rules/confirm_delete.html", {"page_title": "삭제", "obj": obj, "kind": kind})


def _index_url():
    return reverse("blog_rules:index")


def _back(request, anchor=""):
    """보던 날짜(?date= / ?month=)를 지키며 운영 화면으로."""
    keep = request.POST.get("keep", "")
    return redirect(_index_url() + (f"?{keep}" if keep and "/" not in keep else "") + anchor)
