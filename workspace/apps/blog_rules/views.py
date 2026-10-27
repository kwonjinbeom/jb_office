"""블로그·카페 › 운영: 사이트마다 한 줄 (컨셉 · 발행 · 임시저장 · 체크 · 상태). 위쪽 달력 띠로 일별·월별을 고른다.

발행 = 모니터링의 '발행' 계획 + RSS 로 읽은 글 (같은 글은 한 번). 임시저장 = 그날 계획 중 아직 발행 안 한 것.
일별 화면에서 두 숫자를 고치면 그날 값으로 남는다 (SiteDay). 칸을 비우면 다시 자동으로 센 값.
"""
from collections import Counter, OrderedDict
from datetime import date

from django.contrib import messages
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog_ops.models import Plan
from apps.blog_ops.views import published_keys
from apps.core import period

from .forms import BlogForm, RuleForm
from .models import Blog, Rule, SiteDay

FIELDS = ("published", "drafts")


def _nav(request):
    request.nav_key = "blog_rules"


def _values(blogs, lo, hi):
    """(필드, 블로그 pk, 날짜) → 그날 숫자. 고친 값이 있으면 그 값, 없으면 자동으로 센 값."""
    auto = Counter()
    for (pk, d), keys in published_keys(blogs, lo, hi).items():
        auto["published", pk, d] = len(keys)
    for pk, d in (Plan.objects.filter(blog__in=blogs, planned_on__range=(lo, hi))
                  .exclude(status=Plan.Status.PUBLISHED).values_list("blog", "planned_on")):
        auto["drafts", pk, d] += 1
    fixed = {}
    for row in SiteDay.objects.filter(blog__in=blogs, day__range=(lo, hi)):
        for f in FIELDS:
            if getattr(row, f) is not None:
                fixed[f, row.blog_id, row.day] = getattr(row, f)
    return auto, fixed


def _target_days(lo, hi, today):
    """목표를 세는 날 수: 지난 기간은 끝까지, 이번 기간은 오늘까지, 앞으로 올 기간은 전체."""
    if lo > today:
        return (hi - lo).days + 1
    return (min(hi, today) - lo).days + 1


def index(request):
    _nav(request)
    today = timezone.localdate()
    mode, sel = period.parse(request, today)
    start, end = period.bounds(mode, sel)
    strip_lo, strip_hi = period.strip_bounds(mode, sel)
    blogs = list(Blog.objects.prefetch_related("checks"))
    active = [b for b in blogs if b.status == Blog.Status.ACTIVE and b.daily]
    auto, fixed = _values(blogs, strip_lo, strip_hi)

    def value(field, pk, d):
        return fixed.get((field, pk, d), auto[field, pk, d])

    def total(field, pk, lo, hi):
        return sum(value(field, pk, d) for d in period.days_between(lo, hi))

    def state(lo, hi):
        if not active:
            return ""
        days = (hi - lo).days + 1
        return "done" if all(total("published", b.pk, lo, hi) >= b.daily * days for b in active) else "todo"

    days = _target_days(start, end, today)
    for b in blogs:
        b.on = b.status == Blog.Status.ACTIVE
        b.published = total("published", b.pk, start, end)
        b.drafts = total("drafts", b.pk, start, end)
        b.target = b.daily * days if b.on else 0
        b.state = ("done" if b.published >= b.target else "todo") if b.target and start <= today else ""
        if mode == "day":
            b.auto = {f: auto[f, b.pk, sel] for f in FIELDS}
            b.fixed = {f: (f, b.pk, sel) in fixed for f in FIELDS}
        b.meta = " · ".join(x for x in [
            (f"하루 {b.daily}편" + (f" ({b.daily_note})" if b.daily_note else "")) if b.on else b.get_status_display(),
            b.revenue, b.kpi] if x)

    accounts = OrderedDict()  # 같은 계정의 하루 편수 합계 (티스토리: 카카오 계정 단위로 합산된다)
    for b in active:
        if b.account:
            accounts.setdefault(b.account, []).append(b)
    return render(request, "blog_rules/index.html", {
        "page_title": "운영",
        "bar": period.bar(mode, sel, today, state),
        "mode": mode,
        "day": sel,
        "blogs": blogs,
        "published_total": sum(b.published for b in blogs),
        "target_total": sum(b.target for b in blogs),
        "drafts_total": sum(b.drafts for b in blogs),
        "accounts": [(name, sum(b.daily for b in items)) for name, items in accounts.items() if len(items) > 1],
        "keep": request.get_full_path().partition("?")[2],
    })


@require_POST
def count(request):
    """일별 화면에서 발행·임시저장 숫자를 고친다. 비우면 자동으로 센 값으로 돌아간다."""
    blog = get_object_or_404(Blog, pk=request.POST.get("blog") or 0)
    field = request.POST.get("field")
    try:
        day = date.fromisoformat(request.POST.get("day", ""))
    except ValueError:
        day = None
    if field not in FIELDS or day is None:
        return _back(request)
    raw = request.POST.get("value", "").strip()
    value = min(int(raw), 999) if raw.isdigit() else None
    row, _ = SiteDay.objects.get_or_create(blog=blog, day=day)
    setattr(row, field, value)
    if all(getattr(row, f) is None for f in FIELDS):
        row.delete()
    else:
        row.save()
    return _back(request, f"#site-{blog.pk}")


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
    return render(request, "core/confirm_delete.html", {
        "page_title": "삭제", "kind_label": "사이트" if kind == "blog" else "체크", "object_label": str(obj),
        "cancel_url": reverse("blog_rules:index"),
        "crumbs": [("블로그·카페", reverse("blog:list")), ("운영", reverse("blog_rules:index"))]})


def _index_url():
    return reverse("blog_rules:index")


def _back(request, anchor=""):
    """보던 날짜(?date= / ?month=)를 지키며 운영 화면으로."""
    keep = request.POST.get("keep", "")
    return redirect(_index_url() + (f"?{keep}" if keep and "/" not in keep else "") + anchor)
