"""일일루틴: 메뉴마다 한 줄 (할 일 · 결과 · 로컬 실행 · 클라우드 복사 · 상태)과 프롬프트 관리.

프롬프트는 저장소 md (Routine.prompt_doc). 실행할 때는 짧은 안내문(launcher)만 만든다:
날짜·하루 양 + "이 md 를 읽고 따른다" + 오늘의 자료(서버 DB: 사이트·체크, 이미 있는 글, 검색 표준).
클라우드 안내문은 일일루틴/클라우드_제약.md 를 더 읽게 하고, 로컬 안내문 끝에는 진행 보고 부분이 붙는다.

로컬 실행: 화면의 '실행'은 PC 에서 띄운 서버(ROUTINE_LOCAL_URL)의 launch 로 안내문을 보낸다.
PC 서버가 안내문을 workspace/.routine/ 에 쓰고 새 터미널에서 claude 를 연다. 실서버 화면에서 눌러도 PC 에서 돈다.
claude 는 단계마다 `manage.py routine_report` 로 PC DB 에 현황(RoutineRun)을 남긴다.

글쓰기(키 writing): 티스토리·네이버 구분 없이 하루 11편. 그날 쓸 분류·편수는 RoutinePick (없으면 기본 무작위:
광고 수익 하위 6 · 판매 수익 하위 3 · IT/AI 2). 리스트에서 글쓰기 줄을 누르면 왼쪽 아래가 분류 고르기 칸이 된다.
전체 실행: 모든 루틴의 로컬 안내문을 한 번에 이어 붙여 한 터미널에서 차례로 돈다.

프롬프트 최신화: 리스트의 한 줄(루틴 키 prompt_update). 오늘의 자료 'evaluations'(루틴별 평가·점검 관점)를 보고
AI 가 각 루틴의 프롬프트 md 를 고쳐 main 에 올린다. 바뀐 md 는 화면을 열 때 PromptVersion 으로 남는다.
"""
import hashlib
import json
import os
import random
import re
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from django import forms
from django.conf import settings
from django.contrib import messages
from django.db.models import Avg, Max, Q
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.blog_ops.models import FeedEntry
from apps.blog_rules.models import Blog
from apps.core import period

from .models import DATA_CHOICES, Evaluation, PromptVersion, Routine, RoutineDay, RoutinePick, RoutineRun

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
    if key == "writing":
        from apps.naver_writing.models import Post as NaverPost
        from apps.writing.models import Post
        return _by_created(Post, lo, hi) + _by_created(NaverPost, lo, hi)
    if key == "tistory":
        from apps.writing.models import Post
        return _by_created(Post, lo, hi)
    if key == "naver":
        from apps.naver_writing.models import Post
        return _by_created(Post, lo, hi)
    if key == "prompt_update":  # 그날 바뀐 프롬프트 수 (첫 버전은 빼고)
        out = Counter()
        for at in PromptVersion.objects.filter(number__gt=1, captured_at__date__range=(lo, hi)).values_list("captured_at", flat=True):
            out[timezone.localtime(at).date()] += 1
        return out
    return Counter()


# ---- 오늘의 자료 (서버 DB 에서 가져와 안내문에 붙인다)

PLATFORMS = {"tistory": [Blog.Platform.TISTORY], "naver": [Blog.Platform.NAVER]}


def _sites(key):
    lines = []
    blogs = Blog.objects.all() if key == "writing" else Blog.objects.filter(platform__in=PLATFORMS.get(key, []))
    for b in blogs.exclude(status=Blog.Status.HOLD).prefetch_related("checks"):
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
    elif key == "writing":
        from apps.naver_writing.models import Post as NaverPost
        from apps.writing import drafts
        from apps.writing.models import Post
        titles += [d.title for d in drafts.list_drafts()] + [d.title for d in drafts.list_drafts(naver_drafts_dir())]
        for model in (Post, NaverPost):
            titles += list(model.all_objects.order_by("-created_at").values_list("title", flat=True)[:60])
        titles += list(FeedEntry.objects.order_by("-published_at").values_list("title", flat=True)[:80])
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


def _evaluations():
    """루틴마다 프롬프트 md · 점검 관점 · 나의 평가 (마지막으로 프롬프트가 바뀐 뒤 남긴 것은 [새])."""
    blocks = []
    for r in Routine.objects.all():
        since = _last_update(r)
        evals = list(r.evaluations.order_by("-day")[:40])
        new = sum(1 for e in evals if since is None or e.updated_at > since)
        lines = [f"### {r.name} — `{r.prompt_doc or '프롬프트 md 없음'}`",
                 f"점검 관점: {r.review_focus or '(없음)'}", f"나의 평가 ({len(evals)}개, 새 {new}개):"]
        lines += [f"- {e.day} · {e.score}점{' [새]' if since is None or e.updated_at > since else ''} · {e.comment or '(코멘트 없음)'}"
                  for e in evals] or ["- (평가 없음: 점검 관점만으로 손본다)"]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# 글쓰기 기본: 대분류 이름 앞부분 → 그 아래 중분류에서 무작위로 고를 편수
WRITING_MIX = [("광고 수익", 6), ("판매 수익", 3), ("IT/AI", 2)]


def _sections():
    from apps.blog_types.models import Section
    return list(Section.objects.prefetch_related("categories__types"))


def default_picks(day, salt=""):
    """그날의 기본 분류: 날짜로 정해지는 무작위 (같은 날은 같은 결과). salt 를 주면 다시 뽑는다."""
    rng = random.Random(f"{day}{salt}")
    sections = _sections()
    picks = {}
    for prefix, n in WRITING_MIX:
        section = next((s for s in sections if s.name.startswith(prefix)), None)
        cats = list(section.categories.all()) if section else []
        if not cats:
            continue
        chosen = rng.sample(cats, min(n, len(cats)))
        for i in range(n):  # 중분류가 모자라면 같은 중분류에 한 편 더
            sel = chosen[i % len(chosen)].sel
            picks[sel] = picks.get(sel, 0) + 1
    return picks


def day_picks(routine, day):
    """(분류별 편수, 사용자가 고른 것인지)."""
    saved = RoutinePick.objects.filter(routine=routine, day=day).first()
    return (saved.picks, True) if saved else (default_picks(day), False)


def _node_path(sel):
    from apps.blog_types.models import Category, PostType, SubType
    model = {"c": Category, "t": PostType, "s": SubType}.get(sel[:1])
    pk = sel[1:]
    node = model.objects.filter(pk=pk).first() if model and pk.isdigit() else None
    if node is None:
        return None, ""
    if isinstance(node, Category):
        return node, f"{node.section.name} > {node.name}"
    if isinstance(node, PostType):
        return node, f"{node.category.section.name} > {node.category.name} > {node.name}"
    return node, f"{node.post_type.category.section.name} > {node.post_type.category.name} > {node.post_type.name} > {node.name}"


def _picks_text(routine, day):
    picks, custom = day_picks(routine, day)
    lines = [f"(총 {sum(picks.values())}편 · {'사용자가 고른 분류' if custom else '기본: 오늘 무작위'})"]
    for sel, n in picks.items():
        node, path = _node_path(sel)
        if node is None:
            continue
        line = f"- {path} — {n}편"
        cat = node if node.sel.startswith("c") else (node.category if node.sel.startswith("t") else None)
        if cat is not None and (cat.direction or cat.question):
            line += f" (방향: {cat.direction or '-'} / 독자의 질문: {cat.question or '-'})"
        lines.append(line)
    return "\n".join(lines)


def _categories_text():
    lines = []
    for s in _sections():
        lines.append(f"- {s.name}")
        for c in s.categories.all():
            lines.append(f"  - {c.code} {c.name}" + (f" — {c.question}" if c.question else ""))
            lines += [f"    - {t.name}" for t in c.types.all()]
    return "\n".join(lines) or "- (분류 없음)"


DATA_TITLES = {"sites": "사이트·체크 (운영 화면)", "existing": "이미 있는 글 (겹치지 않게)", "standard": "검색 표준 (최신판)",
               "evaluations": "루틴별 평가·점검 관점", "picks": "오늘 쓸 분류", "categories": "글 분류 전체 (대 > 중 > 소)"}


def data_text(routine, key, day):
    if key == "sites":
        return _sites(routine.key)
    if key == "existing":
        return _existing(routine.key, day)
    if key == "standard":
        return _standard(day)
    if key == "evaluations":
        return _evaluations()
    if key == "picks":
        return _picks_text(routine, day)
    if key == "categories":
        return _categories_text()
    return ""


# ---- 안내문

REPORT = """
## 진행 보고 (로컬 실행에 자동으로 붙는 부분)
단계가 바뀔 때마다 저장소 폴더에서 아래 명령으로 일일루틴 화면(로컬 현황)에 한 줄을 남긴다.

    workspace/.venv/Scripts/python workspace/manage.py routine_report {key} <상태> "<한 줄>" --date {day}

- 시작: 맨 처음, 오늘 할 일 한 줄
- 진행: 단계가 바뀔 때 (예: "사이트 최근 글 확인", "원고 2/4편 저장")
- 대기: 권한이 없어 실행이 막혀 내 허락이 필요할 때만 (예: "git push 권한 필요"). 보고하고 기다린다. 그 밖의 판단은 묻지 않고 스스로 한다
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


def restore_prompt(version, mode, day):
    """좋았던 버전으로 되돌리는 안내문: AI 가 프롬프트 md 를 그 버전 내용으로 고쳐 main 에 올린다."""
    routine = version.routine
    lines = [f"# 일일루틴 프롬프트 되돌리기 · {routine.name} v{version.number} — {day} ({'로컬 PC' if mode == 'local' else '클라우드'})", "",
             f"대상 프롬프트: `{routine.prompt_doc}`", "", "## 할 일",
             f"1. 대상 프롬프트를 아래 'v{version.number} 내용'으로 되돌린다 (사용자가 좋았던 버전으로 고름).",
             "2. 맨 아래 '평가에서 배운 점'에 되돌린 날짜와 이유를 한 줄 더한다.",
             f"3. main 에 커밋·push 한다. 커밋 메시지: `prompt: {routine.name} v{version.number} 로 되돌림`."]
    if mode == "cloud":
        lines.append(f"(클라우드: `{CLOUD_DOC}` 도 따른다)")
    lines += ["", f"## v{version.number} 내용", "", version.content]
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

def sends_origin(view):
    """'실행' 폼이 있는 화면: 실서버 → PC 로 보낼 때 Origin 이 실리게 한다.

    Django 기본 Referrer-Policy(same-origin)면 다른 주소로 보내는 POST 의 Origin 이 'null' 이 되어 PC 서버가 거절한다.
    이 화면들만 origin-when-cross-origin (다른 주소에는 주소 앞부분만, 경로는 안 보냄).
    """
    def wrapped(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        response["Referrer-Policy"] = "origin-when-cross-origin"
        return response
    wrapped.__name__, wrapped.__doc__ = view.__name__, view.__doc__
    return wrapped


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


# 로컬 실행 claude 에 미리 허용하는 것: 루틴이 늘 하는 일 (저장소 안 읽기·쓰기, 웹 검색, git 올리기, 진행 보고).
# 묻는 건 권한이 없어 막힐 때만 (2026-10-16 사용자). 방법·선택을 묻는 질문 도구와 브라우저 자동화는 막는다.
ROUTINE_ALLOW = [
    "Read", "Edit", "Write", "Glob", "Grep", "WebSearch", "WebFetch",
    "Bash(git add *)", "Bash(git commit *)", "Bash(git push *)", "Bash(git pull *)", "Bash(git fetch *)",
    "Bash(git status *)", "Bash(git log *)", "Bash(git diff *)", "Bash(ls *)", "Bash(mkdir *)",
    "Bash(workspace/.venv/Scripts/python workspace/manage.py routine_report *)",
    "Bash(workspace/.venv/Scripts/python.exe workspace/manage.py routine_report *)",
]
ROUTINE_DENY = ["AskUserQuestion", "mcp__claude-in-chrome", "mcp__playwright"]
KOREAN = ("모든 말과 진행 보고는 한국어로 한다. 루틴은 스스로 판단해 끝까지 진행하고, 방법·선택·확인을 사용자에게 묻지 않는다. "
          "사용자에게 묻는 건 권한이 없어 실행이 막힐 때뿐이고, 그때는 무엇을 왜 하려는지 한국어로 한 줄 먼저 말한다. "
          "블로그·사이트 확인은 WebFetch·WebSearch 로 하고 브라우저 자동화는 쓰지 않는다. 읽히지 않는 페이지는 막힘으로 보고하고 넘어간다. "
          "셸 명령은 Bash 도구로 저장소 폴더에서 실행한다.")


def _open_terminal(name, title):
    """새 터미널에서 claude 를 연다 (미리 허용한 것 + 한국어). Windows 가 아니면 돌릴 명령을 돌려준다."""
    folder = settings.BASE_DIR / ".routine"
    folder.mkdir(exist_ok=True)
    conf = folder / "settings.json"
    conf.write_text(json.dumps({"permissions": {"allow": ROUTINE_ALLOW, "deny": ROUTINE_DENY}}, ensure_ascii=False, indent=2), encoding="utf-8")
    ask = f"workspace/.routine/{name} 파일을 읽고 그대로 진행해."
    if os.name != "nt":
        return f'claude "{ask}" --settings workspace/.routine/settings.json'
    subprocess.Popen(["cmd", "/c", "start", title, "/D", str(settings.REPO_ROOT), "cmd", "/k", "claude", ask,
                      "--settings", str(conf), "--append-system-prompt", KOREAN])
    return ""


def _cors(request, response):
    origin = request.headers.get("Origin")
    if origin and _origin_ok(request):
        response["Access-Control-Allow-Origin"] = origin
        response["Access-Control-Allow-Methods"] = "POST"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        response["Access-Control-Allow-Private-Network"] = "true"
        response["Vary"] = "Origin"
    return response


def _reply(request, ok, message, day=None):
    """화면의 '실행'은 새 탭 없이 보내고(fmt=json) 결과 한 줄을 받는다. 그 밖에는 예전처럼 PC 화면으로."""
    if request.POST.get("fmt") == "json":
        return _cors(request, JsonResponse({"ok": ok, "message": message}, status=200 if ok else 403))
    if not ok:
        return HttpResponseForbidden(message)
    messages.success(request, message)
    return redirect(f"{reverse('routines:index')}?date={day}#rt-runs")


def _open_run(routine, day, step):
    run = RoutineRun.objects.filter(routine=routine, day=day).first()
    if run is None or not run.is_open:
        run = RoutineRun.objects.create(routine=routine, day=day)
    run.report(RoutineRun.Status.RUNNING, step, timezone.localtime())


def _routine_for(key, name=""):
    return Routine.objects.filter(key=key).first() or Routine.objects.create(
        key=key, name=(name or key)[:40], url_name="routines:index", task="(실서버에서 보낸 루틴)")


@csrf_exempt
def launch(request):
    """안내문을 받아 새 터미널에서 claude 를 연다. PC 서버에서만, 허용한 화면(실서버·PC)에서 보낸 것만."""
    if request.method == "OPTIONS":  # 브라우저가 먼저 묻는 경우 (다른 주소 → PC)
        return _cors(request, HttpResponse(status=204))
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if settings.IS_SERVER:
        return _reply(request, False, "로컬 실행은 PC 에서 띄운 서버에서만 됩니다.")
    if not _origin_ok(request):
        got = request.headers.get("Origin") or "없음"
        return _reply(request, False, f"허용하지 않은 화면에서 보낸 실행 요청입니다. (보낸 곳: {got})")
    key = request.POST.get("key", "")
    text = request.POST.get("prompt", "")
    kind = request.POST.get("kind") if request.POST.get("kind") in ("update", "all") else "run"
    if not re.fullmatch(r"[a-z0-9_-]{1,30}", key) or not text.strip() or len(text) > 600_000:
        return _reply(request, False, "실행 요청이 올바르지 않습니다.")
    day = _day(request)
    folder = settings.BASE_DIR / ".routine"
    folder.mkdir(exist_ok=True)
    if kind == "all":
        keys = [k for k in request.POST.get("keys", "").split(",") if re.fullmatch(r"[a-z0-9_-]{1,30}", k)]
        for k in keys:
            _open_run(_routine_for(k), day, "전체 실행 · 차례를 기다립니다")
        name, title = f"all-{day}.md", "일일루틴 전체 실행"
        done = f"PC 터미널에서 전체 실행을 시작했습니다 ({len(keys)}개 루틴, 차례로)."
    else:
        routine = _routine_for(key, request.POST.get("name", ""))
        label = "갱신" if kind == "update" else "루틴"
        _open_run(routine, day, f"{label} · 터미널을 열었습니다 (claude 시작 대기)")
        name, title = f"{key}-{'update-' if kind == 'update' else ''}{day}.md", f"일일루틴 {routine.name} {label}"
        done = f"PC 터미널에서 {routine.name} {label}을 시작했습니다."
    (folder / name).write_text(text, encoding="utf-8")
    manual = _open_terminal(name, title)
    if manual:
        return _reply(request, True, f"저장소 폴더에서 실행하세요: {manual}", day)
    return _reply(request, True, done + " 진행은 PC 화면의 로컬 현황에 쌓입니다.", day)


def _day(request):
    try:
        return date.fromisoformat(request.POST.get("day", ""))
    except ValueError:
        return timezone.localdate()


def all_prompt(routines, day):
    """전체 실행 안내문: 루틴 순서대로 각 로컬 안내문을 이어 붙인다."""
    head = [f"# 일일루틴 전체 실행 — {day} (로컬 PC)", "",
            "아래 루틴을 위에서부터 차례로 끝까지 진행한다. 오래 걸려도 된다.",
            "- 한 루틴을 끝내고(완료 보고) 다음 루틴으로 넘어간다.",
            "- 한 루틴이 막히면 막힘으로 보고하고 다음 루틴으로 간다. 내가 할 일이 생기면 대기로 보고하고 기다린다.",
            "- 순서: " + " → ".join(f"{i}. {r.name}" for i, r in enumerate(routines, start=1)), ""]
    parts = ["\n".join(head)]
    for i, r in enumerate(routines, start=1):
        parts.append(f"\n{'=' * 8} {i}. {r.name} {'=' * 8}\n\n" + launcher(r, "local", day))
    return "\n".join(parts)


# ---- 분류 고르기 (글쓰기)

def _picker(routine, day):
    picks, custom = day_picks(routine, day)
    tree = []
    for s in _sections():
        cats = []
        for c in s.categories.all():
            cats.append({"obj": c, "n": picks.get(c.sel, 0),
                         "types": [{"obj": t, "n": picks.get(t.sel, 0)} for t in c.types.all()]})
        total = sum(c["n"] + sum(t["n"] for t in c["types"]) for c in cats)
        tree.append({"obj": s, "cats": cats, "n": total})
    from apps.blog_types.models import ClassChange
    return {"routine": routine, "tree": tree, "total": sum(picks.values()), "custom": custom, "day": day,
            "changes": list(ClassChange.objects.all()[:3])}


@require_POST
def picks(request, pk):
    """글쓰기의 그날 분류·편수: 저장 / 다시 뽑기(무작위) / 기본값(그날 무작위)."""
    routine = get_object_or_404(Routine, pk=pk)
    day = _day(request)
    action = request.POST.get("action", "save")
    if action == "default":
        RoutinePick.objects.filter(routine=routine, day=day).delete()
    else:
        if action == "reroll":
            value = default_picks(day, salt=timezone.now().timestamp())
        else:
            value = {}
            for name, raw in request.POST.items():
                sel = name[2:]
                if name.startswith("n_") and re.fullmatch(r"[ct]\d+", sel) and raw.strip().isdigit() and int(raw) > 0:
                    value[sel] = min(int(raw), 20)
        RoutinePick.objects.update_or_create(routine=routine, day=day, defaults={"picks": value})
    return _back(request, "#rt-picker")


# ---- 일일루틴 리스트

@sends_origin
def index(request):
    _nav(request)
    try:  # AI 가 남긴 분류 변경 파일을 먼저 반영한다 (일일루틴/분류변경)
        from apps.blog_types import changes
        changes.sync()
    except Exception:  # 분류 변경이 잘못돼도 화면은 뜬다 (기록은 관리화면)
        pass
    today = timezone.localdate()
    mode, sel = period.parse(request, today)
    start, end = period.bounds(mode, sel)
    lo, hi = period.strip_bounds(mode, sel)
    routines = list(Routine.objects.all())
    for r in routines:  # 프롬프트 md 가 바뀌었으면 버전으로 남긴다 (프롬프트 최신화 결과 수)
        capture_version(r)
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
        if "picks" in r.data_keys and mode == "day":  # 그날 고른 편수가 목표
            r.target = sum(day_picks(r, sel)[0].values())
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
        "all_prompt": all_prompt(routines, run_day) if routines else "",
        "all_keys": ",".join(r.key for r in routines),
        "picker": next((_picker(r, run_day) for r in routines if "picks" in r.data_keys), None),
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

@sends_origin
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


@sends_origin
def version_restore(request, pk):
    """좋았던 버전으로 되돌리는 안내문 (로컬 실행 / 클라우드 복사)."""
    _nav(request, "routine_prompts")
    v = get_object_or_404(PromptVersion, pk=pk)
    today = timezone.localdate()
    return render(request, "routines/restore.html", {
        "page_title": f"{v.routine.name} v{v.number} 로 되돌리기", "version": v, "routine": v.routine, "today": today,
        "on_server": settings.IS_SERVER, "launch_action": launch_action(),
        "local": restore_prompt(v, "local", today), "cloud": restore_prompt(v, "cloud", today)})


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
