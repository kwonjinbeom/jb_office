"""일일루틴: 메뉴마다 한 줄 (할 일 · 결과 · 로컬 실행 · 클라우드 복사 · 상태)과 프롬프트 관리.

프롬프트는 저장소 md (Routine.prompt_doc). 실행할 때는 짧은 안내문(launcher)만 만든다:
날짜·하루 양 + "이 md 를 읽고 따른다" + 오늘의 자료(서버 DB: 사이트·체크, 이미 있는 글, 검색 표준).
클라우드 안내문은 일일루틴/클라우드_제약.md 를 더 읽게 하고, 로컬 안내문 끝에는 진행 보고 부분이 붙는다.

로컬 실행: 화면의 '실행'은 PC 에서 띄운 서버(ROUTINE_LOCAL_URL)의 launch 로 안내문을 보낸다.
PC 서버가 안내문을 workspace/.routine/ 에 쓰고 새 터미널에서 claude 를 연다. 실서버 화면에서 눌러도 PC 에서 돈다.
claude 는 단계마다 `manage.py routine_report` 로 PC DB 에 현황(RoutineRun)을 남긴다.

갱신: 평가(Evaluation)와 루틴의 점검 관점을 담은 갱신 안내문으로 AI 가 프롬프트 md 를 고쳐 main 에 올린다.
바뀐 md 는 프롬프트 관리 화면을 열 때 PromptVersion 으로 남는다.
"""
import hashlib
import os
import re
import subprocess
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from django import forms
from django.conf import settings
from django.contrib import messages
from django.db.models import Avg, Max, Q
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.blog_ops.models import FeedEntry
from apps.blog_rules.models import Blog
from apps.core import period

from .models import DATA_CHOICES, Evaluation, PromptVersion, Routine, RoutineDay, RoutineRun

NAVER_DRAFTS = ("콘텐츠", "블로그_카페", "포스팅자동화", "네이버원고")
CLOUD_DOC = "일일루틴/클라우드_제약.md"


def naver_drafts_dir():
    return settings.REPO_ROOT.joinpath(*NAVER_DRAFTS)


def _screen_choices():
    from apps.core.menus import MENUS
    out = []
    for menu in MENUS:
        for m in (menu, *menu.children):
            if m.url_name and not m.query and m.key not in ("routines", "routine_prompts") and (m.url_name, m.title) not in out:
                out.append((m.url_name, m.title))
    return out


class RoutineForm(forms.ModelForm):
    url_name = forms.ChoiceField(label="화면", choices=())
    data = forms.MultipleChoiceField(label="오늘의 자료", choices=DATA_CHOICES, required=False,
                                     widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Routine
        fields = ["key", "name", "url_name", "task", "output", "daily", "unit", "prompt_doc", "data", "review_focus"]
        widgets = {"review_focus": forms.Textarea(attrs={"rows": 4})}
        help_texts = {"key": "영문 소문자·숫자·_ (진행 보고 명령에 쓰는 이름, 만든 뒤에는 못 바꿈)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        choices = _screen_choices()
        current = self.instance.url_name if self.instance.pk else ""
        if current and current not in dict(choices):  # 메뉴가 바뀌어도 지금 화면은 고를 수 있게
            choices.insert(0, (current, current))
        self.fields["url_name"].choices = choices
        self.initial["data"] = self.instance.data_keys if self.instance.pk else []
        if self.instance.pk:
            self.fields["key"].disabled = True
        for name, field in self.fields.items():
            if name != "data":
                field.widget.attrs.setdefault("class", "input")

    def clean_data(self):
        return ",".join(self.cleaned_data["data"])

    def clean_prompt_doc(self):
        rel = self.cleaned_data["prompt_doc"].strip().replace("\\", "/").lstrip("/")
        if rel and (not rel.endswith(".md") or ".." in rel.split("/")):
            raise forms.ValidationError("저장소 안의 .md 경로로 적으세요.")
        return rel


def _nav(request, key="routines"):
    request.nav_key = key


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


# ---- 오늘의 자료 (서버 DB 에서 가져와 안내문에 붙인다)

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
    elif key in PLATFORMS:
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


DATA_TITLES = {"sites": "사이트·체크 (운영 화면)", "existing": "이미 있는 글 (겹치지 않게)", "standard": "검색 표준 (최신판)"}


def data_text(routine, key, day):
    if key == "sites":
        return _sites(routine.key)
    if key == "existing":
        return _existing(routine.key, day)
    if key == "standard":
        return _standard(day)
    return ""


# ---- 안내문

REPORT = """
## 진행 보고 (로컬 실행에 자동으로 붙는 부분)
단계가 바뀔 때마다 저장소 폴더에서 아래 명령으로 일일루틴 화면(로컬 현황)에 한 줄을 남긴다.

    workspace/.venv/Scripts/python workspace/manage.py routine_report {key} <상태> "<한 줄>" --date {day}

- 시작: 맨 처음, 오늘 할 일 한 줄
- 진행: 단계가 바뀔 때 (예: "사이트 최근 글 확인", "원고 2/4편 저장")
- 대기: 내가 해야 할 일이 있을 때 (예: "티스토리 로그인 필요"). 보고하고 멈춰서 나를 기다린다
- 막힘: 접속 차단·자료 없음 등으로 그 단계를 못 할 때. 이유를 적고 할 수 있는 다음 단계로 간다
- 완료: 끝나면 결과 요약 (예: "원고 4편 저장, main push abc1234")
- 실패: 더 진행할 수 없을 때 이유
"""


def launcher(routine, mode, day):
    """실행 안내문: 날짜·하루 양 + 읽을 md + 오늘의 자료 (+ 로컬이면 진행 보고)."""
    where = "로컬 PC" if mode == "local" else "클라우드"
    lines = [f"# 일일루틴 · {routine.name} — {day} ({where})", "",
             f"오늘 할 일: {routine.task} — 하루 {routine.daily}{routine.unit}.",
             "아래 md 를 읽고 그대로 따른다.", ""]
    lines.append(f"- `{routine.prompt_doc}` (이 루틴의 프롬프트)" if routine.prompt_doc else "- (프롬프트 md 가 아직 없습니다)")
    if mode == "cloud":
        lines.append(f"- `{CLOUD_DOC}` (클라우드 세션 제약)")
    keys = routine.data_keys
    if keys:
        lines += ["", "## 오늘의 자료 (서버에서 가져옴)"]
        for k in keys:
            lines += ["", f"### {DATA_TITLES.get(k, k)}", data_text(routine, k, day)]
    text = "\n".join(lines).rstrip() + "\n"
    if mode == "local":
        text += REPORT.format(key=routine.key, day=day)
    return text


def update_prompt(routine, mode, day, restore=None):
    """갱신 안내문: 평가와 점검 관점으로 프롬프트 md 를 고친다. restore 면 그 버전 내용으로 되돌린다."""
    evals = list(Evaluation.objects.filter(routine=routine).order_by("-day")[:60])
    since = _last_update(routine)
    lines = [f"# 일일루틴 프롬프트 갱신 · {routine.name} — {day} ({'로컬 PC' if mode == 'local' else '클라우드'})", "",
             f"대상 프롬프트: `{routine.prompt_doc}` (로컬·클라우드가 함께 보는 지시)",
             f"클라우드에만 해당하는 제약은 `{CLOUD_DOC}` 에 고친다.", "", "## 할 일"]
    if restore is not None:
        lines += [f"1. 대상 프롬프트를 아래 'v{restore.number} 내용'으로 되돌린다 (사용자가 좋았던 버전으로 고름).",
                  "2. 맨 아래 '평가에서 배운 점'에 되돌린 날짜와 이유를 한 줄 더한다.",
                  f"3. main 에 커밋·push 한다. 커밋 메시지: `prompt: {routine.name} v{restore.number} 로 되돌림`.",
                  "", f"## v{restore.number} 내용", "", restore.content]
    else:
        lines += [
            "1. 대상 프롬프트와 그 안에서 읽게 하는 md 를 읽는다.",
            "2. 아래 '나의 평가'를 분석한다: 점수가 낮은 날과 높은 날의 차이, 코멘트에서 반복되는 요구, [새] 표시 평가를 먼저.",
            f"3. 이 루틴의 일 자체도 점검한다. 갱신 때 볼 관점: {routine.review_focus or '(없음)'}. 필요하면 웹에서 최신 기준(플랫폼 정책 등)을 확인한다.",
            "4. 대상 프롬프트를 고친다. 지시는 짧고 구체적으로, 서로 부딪히는 지시는 정리한다. 맨 아래 '평가에서 배운 점'에 이번 갱신 날짜와 바꾼 이유를 한 줄씩 더한다.",
            "5. 프롬프트 md 만 고친다. 루틴 결과물이나 다른 안내 md 는 고치지 않고, 고칠 점이 있으면 마지막 보고에 적는다.",
            f"6. main 에 커밋·push 한다. 커밋 메시지: `prompt: {routine.name} 갱신 (평가 {len(evals)}개)`.",
            "", "## 나의 평가"]
        for e in evals:
            new = " [새]" if since is None or e.updated_at > since else ""
            lines.append(f"- {e.day} · {e.score}점{new} · {e.comment or '(코멘트 없음)'}")
        if not evals:
            lines.append("- (아직 없음: 점검 관점만으로 손본다)")
        today = timezone.localdate()
        counts = _auto(routine.key, today - timedelta(days=13), today)
        fixed = {d.day: d.done for d in RoutineDay.objects.filter(routine=routine, day__gte=today - timedelta(days=13))}
        lines += ["", f"## 최근 14일 결과 수 (하루 {routine.daily}{routine.unit} 목표)"]
        lines += [f"- {d}: {fixed.get(d, counts[d])}" for d in period.days_between(today - timedelta(days=13), today)]
    if mode == "cloud":
        lines += ["", f"(클라우드: `{CLOUD_DOC}` 도 따른다)"]
    text = "\n".join(lines).rstrip() + "\n"
    if mode == "local":
        text += REPORT.format(key=routine.key, day=day)
    return text


# ---- 프롬프트가 보는 것: 프롬프트 md, 그 안에서 읽게 하는 md, 클라우드 제약, 오늘의 자료

MD_PATH = re.compile(r"(?<![\w가-힣./-])([\w가-힣][\w가-힣./-]*\.md)\b")


def _md_path(rel):
    root = Path(settings.REPO_ROOT).resolve()
    for base in (root, root / "workspace"):
        f = (base / rel).resolve()
        if f.is_file() and root in f.parents:
            return f.relative_to(root).as_posix()
    return None


def _read(rel):
    found = _md_path(rel) if rel else None
    return (Path(settings.REPO_ROOT) / found).read_text(encoding="utf-8") if found else ""


def _reads(text):
    """md 안에서 읽게 하는 md. 쓰는 곳(저장·결과 줄)은 빼고, 짧게 다시 적은 경로는 앞의 전체 경로와 같은 파일로 본다."""
    found = [rel for line in text.splitlines() if not re.search(r"저장|결과", line) for rel in MD_PATH.findall(line)]
    out = []
    for rel in found:
        if not _md_path(rel) and any(r != rel and r.endswith("/" + rel) and _md_path(r) for r in found):
            continue
        if rel not in out:
            out.append(rel)
    return out


def references(routine):
    """[{kind, label, rel, ok}] — 프롬프트 md · 읽는 md · 클라우드 제약 · 오늘의 자료."""
    out = [{"kind": "프롬프트", "label": routine.prompt_doc or "(프롬프트 md 없음)",
            "rel": _md_path(routine.prompt_doc) if routine.prompt_doc else None}]
    seen = {routine.prompt_doc}
    for rel in _reads(_read(routine.prompt_doc)):
        if rel not in seen:
            seen.add(rel)
            out.append({"kind": "읽는 md", "label": rel, "rel": _md_path(rel)})
    out.append({"kind": "클라우드", "label": CLOUD_DOC, "rel": _md_path(CLOUD_DOC)})
    for ref in out:
        ref["ok"] = bool(ref["rel"])
    out += [{"kind": "자료", "label": DATA_TITLES.get(k, k), "rel": None, "ok": True, "data": k} for k in routine.data_keys]
    return out


def _docs_of(routine):
    return {ref["rel"] for ref in references(routine) if ref["rel"]}


def capture_version(routine):
    """프롬프트 md 가 마지막 버전과 다르면 새 버전으로 남긴다."""
    content = _read(routine.prompt_doc)
    if not content:
        return None
    sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
    last = routine.versions.first()
    if last and last.sha == sha:
        return last
    return PromptVersion.objects.create(routine=routine, number=(last.number + 1) if last else 1, sha=sha, content=content)


def _last_update(routine):
    """마지막 갱신 시각 = 첫 버전 뒤에 새로 남은 버전의 시각. 그 뒤에 남긴 평가가 '새 평가'."""
    last = routine.versions.first()
    return last.captured_at if last and last.number > 1 else None


# ---- 로컬 실행 (PC 서버의 launch 로 보낸다)

def launch_action():
    """'실행' 폼이 보낼 곳. PC 서버면 같은 서버, 실서버면 PC 서버(ROUTINE_LOCAL_URL)."""
    path = reverse("routines:launch")
    return settings.ROUTINE_LOCAL_URL.rstrip("/") + path if settings.IS_SERVER else path


def _origin_ok(request):
    origin = request.headers.get("Origin", "")
    if not origin:
        return False
    parts = urlsplit(origin)
    origin = f"{parts.scheme}://{parts.netloc}"
    allowed = {f"{request.scheme}://{request.get_host()}", *settings.ROUTINE_LAUNCH_ORIGINS}
    return origin in {a.rstrip("/") for a in allowed}


@csrf_exempt
@require_POST
def launch(request):
    """안내문을 받아 새 터미널에서 claude 를 연다. PC 서버에서만, 허용한 화면(실서버·PC)에서 보낸 것만."""
    if settings.IS_SERVER:
        return HttpResponseForbidden("로컬 실행은 PC 에서 띄운 서버에서만 됩니다.")
    if not _origin_ok(request):
        return HttpResponseForbidden("허용하지 않은 화면에서 보낸 실행 요청입니다.")
    key = request.POST.get("key", "")
    text = request.POST.get("prompt", "")
    kind = "update" if request.POST.get("kind") == "update" else "run"
    if not re.fullmatch(r"[a-z0-9_-]{1,30}", key) or not text.strip() or len(text) > 200_000:
        return HttpResponseForbidden("실행 요청이 올바르지 않습니다.")
    try:
        day = date.fromisoformat(request.POST.get("day", ""))
    except ValueError:
        day = timezone.localdate()
    routine = Routine.objects.filter(key=key).first() or Routine.objects.create(
        key=key, name=request.POST.get("name", key)[:40] or key, url_name="routines:index", task="(실서버에서 보낸 루틴)")
    folder = settings.BASE_DIR / ".routine"
    folder.mkdir(exist_ok=True)
    name = f"{key}-{'update-' if kind == 'update' else ''}{day}.md"
    (folder / name).write_text(text, encoding="utf-8")
    label = "갱신" if kind == "update" else "루틴"
    run = RoutineRun.objects.filter(routine=routine, day=day).first()
    if run is None or not run.is_open:
        run = RoutineRun.objects.create(routine=routine, day=day)
    run.report(RoutineRun.Status.RUNNING, f"{label} · 터미널을 열었습니다 (claude 시작 대기)", timezone.localtime())
    ask = f"Read workspace/.routine/{name} and follow it exactly."
    if os.name == "nt":
        subprocess.Popen(["cmd", "/c", "start", f"일일루틴 {routine.name} {label}", "/D", str(settings.REPO_ROOT),
                          "cmd", "/k", "claude", ask])
        messages.success(request, f"새 터미널에서 {routine.name} {label}을 시작했습니다. 아래 로컬 현황에 단계가 쌓입니다.")
    else:
        messages.info(request, f'저장소 폴더에서 실행하세요: claude "{ask}"')
    return redirect(f"{reverse('routines:index')}?date={day}#rt-runs")


# ---- 일일루틴 리스트

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
    run_day = sel if mode == "day" else today
    for r in routines:
        r.result = total(r, start, end)
        r.target = r.daily * days
        r.state = ("done" if r.result >= r.target else "todo") if r.target and start <= today else ""
        r.auto = auto[r.pk][sel]
        r.fixed = (r.pk, sel) in fixed
        r.url = reverse(r.url_name)
        r.local_prompt = launcher(r, "local", run_day)
        r.cloud_prompt = launcher(r, "cloud", run_day)
    runs = (RoutineRun.objects.select_related("routine")
            .filter(Q(day__range=(start, end)) | Q(status__in=[RoutineRun.Status.RUNNING, RoutineRun.Status.WAITING,
                                                                 RoutineRun.Status.BLOCKED]))[:30])
    return render(request, "routines/index.html", {
        "page_title": "일일루틴",
        "bar": period.bar(mode, sel, today, state),
        "mode": mode,
        "day": sel,
        "run_day": run_day,
        "routines": routines,
        "done_total": sum(1 for r in routines if r.state == "done"),
        "runs": runs,
        "has_open_run": any(run.is_open for run in runs),
        "on_server": settings.IS_SERVER,
        "launch_action": launch_action(),
        "local_url": settings.ROUTINE_LOCAL_URL.rstrip("/") + reverse("routines:index"),
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


# ---- 프롬프트 관리 (루틴 탭: 왼쪽 프롬프트 md·자료, 오른쪽 나의 평가·갱신·이력)

def prompts(request):
    _nav(request, "routine_prompts")
    routines = list(Routine.objects.all())
    if not routines:
        return render(request, "routines/prompts.html", {"page_title": "프롬프트 관리", "routines": []})
    routine = next((r for r in routines if r.key == request.GET.get("r")), routines[0])
    capture_version(routine)
    today = timezone.localdate()
    refs = references(routine)
    from apps.docs.views import _render
    for ref in refs:
        if ref.get("data"):
            ref["text"] = data_text(routine, ref["data"], today)
        elif ref["rel"]:
            ref["html"], _ = _render(_read(ref["rel"]))
    since = _last_update(routine)
    evals = list(routine.evaluations.all()[:60])
    for e in evals:
        e.is_new = since is None or e.updated_at > since
    return render(request, "routines/prompts.html", {
        "page_title": "프롬프트 관리",
        "routines": routines,
        "routine": routine,
        "refs": refs,
        "evals": evals,
        "new_count": sum(1 for e in evals if e.is_new),
        "avg": routine.evaluations.aggregate(avg=Avg("score"))["avg"],
        "versions": list(routine.versions.all()[:30]),
        "today": today,
        "on_server": settings.IS_SERVER,
        "launch_action": launch_action(),
        "update_local": update_prompt(routine, "local", today),
        "update_cloud": update_prompt(routine, "cloud", today),
    })


def _prompts_url(routine, anchor=""):
    return f"{reverse('routines:prompts')}?r={routine.key}{anchor}"


@require_POST
def evaluate(request, pk):
    routine = get_object_or_404(Routine, pk=pk)
    try:
        day = date.fromisoformat(request.POST.get("day", ""))
        score = int(request.POST.get("score", ""))
    except ValueError:
        messages.warning(request, "날짜와 평점을 고르세요.")
        return redirect(_prompts_url(routine, "#pm-eval"))
    if not 1 <= score <= 5:
        messages.warning(request, "평점은 1~5점입니다.")
        return redirect(_prompts_url(routine, "#pm-eval"))
    comment = request.POST.get("comment", "").strip()[:2000]
    Evaluation.objects.update_or_create(routine=routine, day=day, defaults={"score": score, "comment": comment})
    return redirect(_prompts_url(routine, "#pm-eval"))


@require_POST
def evaluation_delete(request, pk):
    e = get_object_or_404(Evaluation, pk=pk)
    e.delete()  # 휴지통으로
    messages.success(request, "평가를 휴지통으로 옮겼습니다.")
    return redirect(_prompts_url(e.routine, "#pm-eval"))


@require_POST
def version_star(request, pk):
    v = get_object_or_404(PromptVersion, pk=pk)
    v.starred = not v.starred
    v.save(update_fields=["starred"])
    return redirect(_prompts_url(v.routine, "#pm-history"))


def version_restore(request, pk):
    """좋았던 버전으로 되돌리는 갱신 안내문 (로컬 실행 / 클라우드 복사)."""
    _nav(request, "routine_prompts")
    v = get_object_or_404(PromptVersion, pk=pk)
    today = timezone.localdate()
    return render(request, "routines/restore.html", {
        "page_title": f"{v.routine.name} v{v.number} 로 되돌리기", "version": v, "routine": v.routine, "today": today,
        "on_server": settings.IS_SERVER, "launch_action": launch_action(),
        "local": update_prompt(v.routine, "local", today, restore=v), "cloud": update_prompt(v.routine, "cloud", today, restore=v)})


def doc(request, rel):
    """프롬프트가 보는 md 를 읽기 전용으로. 루틴이 보는 파일만 연다."""
    _nav(request, "routine_prompts")
    used = [r for r in Routine.objects.all() if rel in _docs_of(r)]
    if not used:
        raise Http404
    from apps.docs.views import _render
    body, _ = _render(_read(rel))
    return render(request, "routines/doc.html", {"page_title": Path(rel).name, "rel": rel, "html": body, "used": used})


def edit(request, pk=None):
    _nav(request, "routine_prompts")
    routine = get_object_or_404(Routine, pk=pk) if pk else None
    form = RoutineForm(request.POST or None, instance=routine)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if not routine:
            saved.order = (Routine.all_objects.aggregate(m=Max("order"))["m"] or 0) + 1
        saved.save()
        messages.success(request, f"'{saved.name}' 루틴을 저장했습니다.")
        return redirect(_prompts_url(saved))
    return render(request, "routines/form.html", {
        "page_title": f"{routine.name} 루틴" if routine else "새 루틴", "form": form, "routine": routine})


def delete(request, pk):
    _nav(request, "routine_prompts")
    routine = get_object_or_404(Routine, pk=pk)
    if request.method == "POST":
        routine.delete()  # 휴지통으로 (7일 동안 복원)
        messages.success(request, f"'{routine.name}' 루틴을 휴지통으로 옮겼습니다.")
        return redirect("routines:prompts")
    return render(request, "routines/confirm_delete.html", {"page_title": "삭제", "routine": routine})
