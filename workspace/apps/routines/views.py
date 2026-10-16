"""일일루틴: 메뉴마다 한 줄 (할 일 · 결과 · 로컬 · 클라우드 · 상태). 위쪽 달력 띠는 운영 화면과 같다.

결과는 각 화면에 그날 생긴 수를 자동으로 센다 (일일 아이디어 = 그날 조사 후보, 글쓰기 = 그날 만든 템플릿).
일별 화면에서 숫자를 고치면 그날 값으로 남는다 (RoutineDay). 비우면 다시 자동.
로컬 실행은 이 PC 에서 돌리는 개발 서버에서만: 프롬프트를 workspace/.routine/ 에 쓰고 새 터미널에서 claude 를 연다.
로컬 프롬프트 끝에는 진행 보고 부분이 자동으로 붙어, claude 가 `manage.py routine_report` 로 현황(RoutineRun)을 남긴다.
프롬프트 관리: 루틴마다 로컬·클라우드 프롬프트와 그 프롬프트가 보는 md·자료를 보여 주고 고친다.
"""
import os
import re
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib import messages
from django.db.models import Max, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog_ops.models import FeedEntry
from apps.blog_rules.models import Blog
from apps.core import period

from .models import Routine, RoutineDay, RoutineRun

NAVER_DRAFTS = ("콘텐츠", "블로그_카페", "포스팅자동화", "네이버원고")


def naver_drafts_dir():
    return settings.REPO_ROOT.joinpath(*NAVER_DRAFTS)


def _screen_choices():
    from apps.core.menus import MENUS
    out = []
    for menu in MENUS:
        for m in (menu, *menu.children):
            if m.url_name and not m.query and m.key != "routines" and (m.url_name, m.title) not in out:
                out.append((m.url_name, m.title))
    return out


class RoutineForm(forms.ModelForm):
    url_name = forms.ChoiceField(label="화면", choices=())

    class Meta:
        model = Routine
        fields = ["key", "name", "url_name", "task", "output", "daily", "unit", "prompt_local", "prompt_cloud"]
        widgets = {"prompt_local": forms.Textarea(attrs={"rows": 18}), "prompt_cloud": forms.Textarea(attrs={"rows": 18})}
        help_texts = {"key": "영문 소문자·숫자·_ (진행 보고 명령에 쓰는 이름, 만든 뒤에는 못 바꿈)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        self.fields["url_name"].choices = _screen_choices()
        if self.instance.pk:
            self.fields["key"].disabled = True
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


# 로컬 프롬프트 끝에 자동으로 붙는 부분. claude 가 단계마다 화면(로컬 현황)에 한 줄을 남긴다.
REPORT = """

## 진행 보고 (로컬 실행에 자동으로 붙는 부분)
단계가 바뀔 때마다 저장소 폴더에서 아래 명령으로 일일루틴 화면(로컬 현황)에 한 줄을 남긴다.

    workspace/.venv/Scripts/python workspace/manage.py routine_report {키} <상태> "<한 줄>" --date {날짜}

- 시작: 맨 처음, 오늘 할 일 한 줄
- 진행: 단계가 바뀔 때 (예: "사이트 최근 글 확인", "원고 2/4편 저장")
- 대기: 내가 해야 할 일이 있을 때 (예: "티스토리 로그인 필요"). 보고하고 멈춰서 나를 기다린다
- 막힘: 접속 차단·자료 없음 등으로 그 단계를 못 할 때. 이유를 적고 할 수 있는 다음 단계로 간다
- 완료: 끝나면 결과 요약 (예: "원고 4편 저장, main push abc1234")
- 실패: 더 진행할 수 없을 때 이유
"""


def render_prompt(routine, mode, day):
    text = routine.prompt_local if mode == "local" else routine.prompt_cloud
    if mode == "local":
        text = text.rstrip() + REPORT
    fills = {"{날짜}": lambda: day.isoformat(), "{하루양}": lambda: f"{routine.daily}{routine.unit}",
             "{키}": lambda: routine.key,
             "{사이트}": lambda: _sites(routine.key), "{기존글}": lambda: _existing(routine.key, day),
             "{검색표준}": lambda: _standard(day)}
    for mark, fill in fills.items():
        if mark in text:
            text = text.replace(mark, fill())
    return text.strip() + "\n"


# ---- 프롬프트가 보는 것: 본문에 적힌 md 파일 + 바뀌는 칸이 가져오는 자료

MD_PATH = re.compile(r"(?<![\w가-힣./-])([\w가-힣][\w가-힣./-]*\.md)\b")


def _md_path(rel):
    for base in (settings.REPO_ROOT, settings.REPO_ROOT / "workspace"):
        f = (Path(base) / rel).resolve()
        if f.is_file() and Path(settings.REPO_ROOT).resolve() in f.parents:
            return f.relative_to(Path(settings.REPO_ROOT).resolve()).as_posix()
    return None


def references(routine, text):
    """[{label, url, ok, note}] — md 는 저장소에 있는지(ok)와 볼 주소, 자료는 어디서 오는지."""
    from apps.daily_ideas.standard import METHOD_DOC
    out, seen = [], set()

    def md(rel, note=""):
        found = _md_path(rel)
        key = found or rel
        if key in seen:
            return
        seen.add(key)
        out.append({"label": rel, "rel": found, "url": reverse("routines:doc", args=[found]) if found else "",
                    "ok": bool(found), "note": note})

    # 쓰는 곳(저장·결과 줄)은 빼고 읽는 md 만. 짧게 다시 적은 경로(원고/README.md)는 앞에서 찾은 전체 경로와 같은 파일.
    reads = [rel for line in text.splitlines() if not re.search(r"저장|결과", line) for rel in MD_PATH.findall(line)]
    for rel in reads:
        if not _md_path(rel) and any(r != rel and r.endswith("/" + rel) and _md_path(r) for r in reads):
            continue
        md(rel)
    if "{검색표준}" in text:
        md(METHOD_DOC, "검색 표준 안")
        out.append({"label": "검색 표준 (최신판)", "url": reverse("daily_ideas:standard"), "ok": True, "note": "자료"})
    if "{사이트}" in text:
        out.append({"label": "운영: 사이트 컨셉·체크", "url": reverse("blog_rules:index"), "ok": True, "note": "자료"})
    if "{기존글}" in text:
        label = "지난 후보 (일일아이디어 JSON)" if routine.key == "daily_ideas" else "이미 있는 글 (글쓰기·RSS·원고 폴더)"
        out.append({"label": label, "url": "", "ok": True, "note": "자료"})
    return out


def _docs_of(routine):
    return {ref["rel"] for text in (routine.prompt_local, routine.prompt_cloud)
            for ref in references(routine, text) if ref.get("rel")}


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
    runs = (RoutineRun.objects.select_related("routine")
            .filter(Q(day__range=(start, end)) | Q(status__in=[RoutineRun.Status.RUNNING, RoutineRun.Status.WAITING,
                                                                 RoutineRun.Status.BLOCKED]))[:20])
    return render(request, "routines/index.html", {
        "page_title": "일일루틴",
        "bar": period.bar(mode, sel, today, state),
        "mode": mode,
        "day": sel,
        "routines": routines,
        "done_total": sum(1 for r in routines if r.state == "done"),
        "runs": runs,
        "has_open_run": any(run.is_open for run in runs),
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
    run = RoutineRun.objects.filter(routine=routine, day=day).first()
    if run is None or not run.is_open:
        run = RoutineRun.objects.create(routine=routine, day=day)
    run.report(RoutineRun.Status.RUNNING, "터미널을 열었습니다 (claude 시작 대기)", timezone.localtime())
    if os.name == "nt":
        subprocess.Popen(["cmd", "/c", "start", f"일일루틴 {routine.name}", "/D", str(settings.REPO_ROOT),
                          "cmd", "/k", "claude", ask])
        messages.success(request, f"새 터미널에서 {routine.name} 루틴을 시작했습니다.")
    else:
        messages.info(request, f'저장소 폴더에서 실행하세요: claude "{ask}"')
    return _back(request, f"#rt-{routine.key}")


def _prompt_nav(request):
    request.nav_key = "routine_prompts"


def prompts(request):
    """프롬프트 관리: 루틴마다 로컬·클라우드 프롬프트(원문)와 그 프롬프트가 보는 md·자료."""
    _prompt_nav(request)
    rows = []
    for r in Routine.objects.all():
        for mode, label, text in (("local", "로컬", r.prompt_local), ("cloud", "클라우드", r.prompt_cloud)):
            rows.append({"routine": r, "mode": mode, "label": label, "text": text, "first": mode == "local",
                         "refs": references(r, text + (REPORT if mode == "local" else "")),
                         "marks": [m for m in ("{날짜}", "{하루양}", "{사이트}", "{기존글}", "{검색표준}") if m in text]})
    return render(request, "routines/prompts.html", {"page_title": "프롬프트 관리", "rows": rows})


def edit(request, pk=None):
    _prompt_nav(request)
    routine = get_object_or_404(Routine, pk=pk) if pk else None
    form = RoutineForm(request.POST or None, instance=routine)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if not routine:
            saved.order = (Routine.all_objects.aggregate(m=Max("order"))["m"] or 0) + 1
        saved.save()
        messages.success(request, f"'{saved.name}' 루틴을 저장했습니다.")
        return redirect("routines:prompts")
    return render(request, "routines/form.html", {
        "page_title": f"{routine.name} 루틴" if routine else "새 루틴", "form": form, "routine": routine})


def delete(request, pk):
    _prompt_nav(request)
    routine = get_object_or_404(Routine, pk=pk)
    if request.method == "POST":
        routine.delete()  # 휴지통으로 (7일 동안 복원)
        messages.success(request, f"'{routine.name}' 루틴을 휴지통으로 옮겼습니다.")
        return redirect("routines:prompts")
    return render(request, "routines/confirm_delete.html", {"page_title": "삭제", "routine": routine})


def doc(request, rel):
    """프롬프트가 보는 md 를 읽기 전용으로. 루틴 프롬프트에 적힌 파일만 연다."""
    _prompt_nav(request)
    used = [r for r in Routine.objects.all() if rel in _docs_of(r)]
    if not used:
        raise Http404
    from apps.docs.views import _render
    path = Path(settings.REPO_ROOT) / rel
    body, toc = _render(path.read_text(encoding="utf-8"))
    return render(request, "routines/doc.html", {"page_title": path.name, "rel": rel, "html": body, "used": used})
