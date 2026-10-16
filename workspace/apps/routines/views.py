"""일일루틴: 메뉴마다 한 줄 (할 일 · 결과 · 로컬 · 클라우드 · 상태). 위쪽 달력 띠는 운영 화면과 같다.

결과는 각 화면에 그날 생긴 수를 자동으로 센다 (일일 아이디어 = 그날 조사 후보, 글쓰기 = 그날 만든 템플릿).
일별 화면에서 숫자를 고치면 그날 값으로 남는다 (RoutineDay). 비우면 다시 자동.
로컬 실행은 이 PC 에서 돌리는 개발 서버에서만: 프롬프트를 workspace/.routine/ 에 쓰고 새 터미널에서 claude 를 연다.
"""
import os
import subprocess
from collections import Counter
from datetime import date

from django import forms
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog_ops.models import FeedEntry
from apps.blog_rules.models import Blog
from apps.core import period

from .models import Routine, RoutineDay

NAVER_DRAFTS = ("콘텐츠", "블로그_카페", "포스팅자동화", "네이버원고")


def naver_drafts_dir():
    return settings.REPO_ROOT.joinpath(*NAVER_DRAFTS)


class RoutineForm(forms.ModelForm):
    class Meta:
        model = Routine
        fields = ["name", "task", "output", "daily", "unit", "prompt_local", "prompt_cloud"]
        widgets = {"prompt_local": forms.Textarea(attrs={"rows": 18}), "prompt_cloud": forms.Textarea(attrs={"rows": 18})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


def _nav(request):
    request.nav_key = "routines"


# ---- 자동으로 세는 결과 (날짜 → 수)

def _by_created(model, lo, hi):
    out = Counter()
    for created in model.objects.filter(created_at__date__range=(lo, hi)).values_list("created_at", flat=True):
        out[timezone.localtime(created).date()] += 1
    return out


def _auto(key, lo, hi):
    if key == "daily_ideas":
        from apps.daily_ideas.data import load_batches
        out = Counter()
        for batch in load_batches():
            d = date.fromisoformat(batch["date"])
            if lo <= d <= hi:
                out[d] += len(batch["items"])
        return out
    if key == "tistory":
        from apps.writing.models import Post
        return _by_created(Post, lo, hi)
    if key == "naver":
        from apps.naver_writing.models import Post
        return _by_created(Post, lo, hi)
    return Counter()


# ---- 프롬프트에 넣는 바뀌는 칸

PLATFORMS = {"tistory": [Blog.Platform.TISTORY], "naver": [Blog.Platform.NAVER]}


def _sites(key):
    lines = []
    for b in Blog.objects.filter(platform__in=PLATFORMS.get(key, [])).exclude(status=Blog.Status.HOLD).prefetch_related("checks"):
        head = f"- {b.name} ({b.address or '주소 없음'}) · {b.content or '컨셉 미정'}"
        head += f" · 하루 {b.daily}편" if b.status == Blog.Status.ACTIVE else f" · {b.get_status_display()}"
        lines.append(head)
        lines += [f"  - 체크: {c.body}" for c in b.checks.all()]
    return "\n".join(lines) or "- (해당 사이트 없음)"


def _existing(key, day):
    titles = []
    if key == "daily_ideas":
        from apps.daily_ideas.data import load_batches
        for batch in load_batches():
            if batch["date"] < day.isoformat():
                titles += [f"{batch['date']} · {item['title']}" for item in batch["items"]]
            if len(titles) >= 80:
                break
    else:
        from apps.writing import drafts
        if key == "tistory":
            from apps.writing.models import Post
            folder = None
        else:
            from apps.naver_writing.models import Post
            folder = naver_drafts_dir()
        titles += [d.title for d in drafts.list_drafts(folder)]
        titles += list(Post.all_objects.order_by("-created_at").values_list("title", flat=True)[:60])
        titles += list(FeedEntry.objects.filter(blog__platform__in=PLATFORMS[key])
                       .order_by("-published_at").values_list("title", flat=True)[:60])
    seen, out = set(), []
    for t in titles:
        if t and t not in seen:
            seen.add(t)
            out.append(f"- {t}")
    return "\n".join(out[:120]) or "- (아직 없음)"


def _standard(day):
    from apps.daily_ideas.models import SearchStandard
    from apps.daily_ideas.standard import request_text
    standard = SearchStandard.objects.order_by("-version").first()
    if standard is None:
        return "(검색 표준이 아직 없습니다. 일일 아이디어 › 검색 표준에서 먼저 저장하세요.)"
    return request_text(standard, day.isoformat())


def render_prompt(routine, mode, day):
    text = routine.prompt_local if mode == "local" else routine.prompt_cloud
    fills = {"{날짜}": lambda: day.isoformat(), "{하루양}": lambda: f"{routine.daily}{routine.unit}",
             "{사이트}": lambda: _sites(routine.key), "{기존글}": lambda: _existing(routine.key, day),
             "{검색표준}": lambda: _standard(day)}
    for mark, fill in fills.items():
        if mark in text:
            text = text.replace(mark, fill())
    return text.strip() + "\n"


# ---- 화면

def index(request):
    _nav(request)
    today = timezone.localdate()
    mode, sel = period.parse(request, today)
    start, end = period.bounds(mode, sel)
    lo, hi = period.strip_bounds(mode, sel)
    routines = list(Routine.objects.all())
    fixed = {(r.routine_id, r.day): r.done for r in RoutineDay.objects.filter(day__range=(lo, hi))}
    auto = {r.pk: _auto(r.key, lo, hi) for r in routines}

    def total(r, a, b):
        return sum(fixed.get((r.pk, d), auto[r.pk][d]) for d in period.days_between(a, b))

    def state(a, b):
        days = (b - a).days + 1
        targets = [r for r in routines if r.daily]
        if not targets:
            return ""
        return "done" if all(total(r, a, b) >= r.daily * days for r in targets) else "todo"

    days = (end - start).days + 1 if start > today else (min(end, today) - start).days + 1
    for r in routines:
        r.result = total(r, start, end)
        r.target = r.daily * days
        r.state = ("done" if r.result >= r.target else "todo") if r.target and start <= today else ""
        r.auto = auto[r.pk][sel]
        r.fixed = (r.pk, sel) in fixed
        r.url = reverse(r.url_name)
        r.local_prompt = render_prompt(r, "local", sel if mode == "day" else today)
        r.cloud_prompt = render_prompt(r, "cloud", sel if mode == "day" else today)
    return render(request, "routines/index.html", {
        "page_title": "일일루틴",
        "bar": period.bar(mode, sel, today, state),
        "mode": mode,
        "day": sel,
        "routines": routines,
        "done_total": sum(1 for r in routines if r.state == "done"),
        "local_run": not settings.IS_SERVER,
        "keep": request.get_full_path().partition("?")[2],
    })


def _back(request, anchor=""):
    keep = request.POST.get("keep", "")
    return redirect(reverse("routines:index") + (f"?{keep}" if keep else "") + anchor)


@require_POST
def count(request, pk):
    routine = get_object_or_404(Routine, pk=pk)
    try:
        day = date.fromisoformat(request.POST.get("day", ""))
    except ValueError:
        return _back(request)
    raw = request.POST.get("value", "").strip()
    if raw.isdigit():
        RoutineDay.objects.update_or_create(routine=routine, day=day, defaults={"done": min(int(raw), 999)})
    else:
        RoutineDay.objects.filter(routine=routine, day=day).delete()
    return _back(request, f"#rt-{routine.key}")


@require_POST
def run_local(request, pk):
    """이 PC 의 개발 서버에서만: 로컬 프롬프트를 파일로 쓰고 새 터미널에서 claude 를 연다 (권한은 터미널에서 직접 승인)."""
    routine = get_object_or_404(Routine, pk=pk)
    if settings.IS_SERVER:
        messages.warning(request, "로컬 실행은 PC 에서 띄운 서버에서만 됩니다. 여기서는 프롬프트를 복사해 쓰세요.")
        return _back(request)
    try:
        day = date.fromisoformat(request.POST.get("day", ""))
    except ValueError:
        day = timezone.localdate()
    folder = settings.BASE_DIR / ".routine"
    folder.mkdir(exist_ok=True)
    name = f"{routine.key}-{day}.md"
    (folder / name).write_text(render_prompt(routine, "local", day), encoding="utf-8")
    ask = f"Read workspace/.routine/{name} and follow it exactly."
    if os.name == "nt":
        subprocess.Popen(["cmd", "/c", "start", f"일일루틴 {routine.name}", "/D", str(settings.REPO_ROOT),
                          "cmd", "/k", "claude", ask])
        messages.success(request, f"새 터미널에서 {routine.name} 루틴을 시작했습니다.")
    else:
        messages.info(request, f'저장소 폴더에서 실행하세요: claude "{ask}"')
    return _back(request, f"#rt-{routine.key}")


def edit(request, pk):
    _nav(request)
    routine = get_object_or_404(Routine, pk=pk)
    form = RoutineForm(request.POST or None, instance=routine)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "저장했습니다.")
        return redirect("routines:index")
    return render(request, "routines/form.html", {"page_title": f"{routine.name} 루틴", "form": form, "routine": routine})
