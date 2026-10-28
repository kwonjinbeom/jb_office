"""일일루틴: 메뉴마다 한 줄 (할 일 · 결과 · 실행 · 상태)과 프롬프트 관리.

프롬프트는 저장소 md (Routine.prompt_doc). 실행할 때는 짧은 안내문(launcher)만 만든다:
날짜·하루 양 + "이 md 를 읽고 따른다" + 오늘의 자료(서버 DB: 사이트·체크, 이미 있는 글, 검색 표준).
로컬·클라우드 구분은 없다 (2026-10-17 사용자). 진행 보고는 서버의 보고 주소(report_api)로 보내 '실행 이력'에 쌓인다
(토큰이 없으면 PC 의 manage.py routine_report).
모든 실행은 PC 에서 손으로 한다 (2026-10-17 사용자: 클라우드 예약은 지웠다). 리스트의 '실행'(루틴 하나),
'전체 실행'(ALL_ORDER 순서로 루틴마다 새 터미널에서 차례로). 하루 분량과 따로 더 쓰는 건 중메뉴 '커스텀 글쓰기'
(topics.py — 사이트별 소재·고정 주제를 골라 편수만큼, 또는 자유 글쓰기 코멘트). 예전 중메뉴 '추가 실행'은 2026-10-23 뺐다.
보고 토큰은 설정 화면에서 만든다 (AppSetting 'routine_brief_token'). 결과는 main 에 올라가 웹훅으로 서버에 반영된다.

로컬 실행: 화면의 '실행'은 안내문을 클립보드에 복사하고 jbroutine: 링크로 PC 에서 claude 터미널을 연다 (local_run.py).
PC 서버가 꺼져 있어도 된다. claude 는 단계마다 `manage.py routine_report` 로 PC DB 에 현황(RoutineRun)을 남긴다.

글쓰기(키 writing): 글 분류 = 사이트 > 고정 소재 (2026-10-22 사용자). 그날 쓸 분류·편수는 RoutinePick (없으면 기본:
모든 소재 한 편씩 — 소재가 있는 것만 쓰고 없으면 쓰지 않는다, 주제 기획이 가린다). 리스트에서 글쓰기 줄을 누르면 커스텀 글쓰기 목록이 펼쳐진다.
전체 실행: 모든 루틴의 로컬 안내문을 이어 붙여 보내고, PC 가 루틴마다 나눠 새 터미널에서 차례로 돌린다 (local_run.open_chain).

프롬프트 최신화: 리스트의 한 줄(루틴 키 prompt_update). 오늘의 자료 'evaluations'(루틴별 평가·점검 관점)를 보고
AI 가 각 루틴의 프롬프트 md 를 고쳐 main 에 올린다. 바뀐 md 는 화면을 열 때 PromptVersion 으로 남는다.
"""
import hashlib
import hmac
import random
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlencode

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.db.models import Avg, Max, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.blog_ops.models import FeedEntry
from apps.blog_rules.models import Blog
from apps.core import period
from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting

from .models import DATA_CHOICES, Evaluation, PromptVersion, Routine, RoutineDay, RoutinePick, RoutineRun

NAVER_DRAFTS = ("콘텐츠", "블로그_카페", "포스팅자동화", "네이버원고")


def naver_drafts_dir():
    return settings.REPO_ROOT.joinpath(*NAVER_DRAFTS)


def _screen_choices():
    from apps.core.menus import walk
    out = []
    for m in walk():
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
    """사이트마다 컨셉 · 체크 + 사이트별 템플릿(말투·구성·꼭 지킬 것) + 카테고리 컨셉.
    글을 처음 쓸 때부터 그 사이트·카테고리 컨셉에 맞춰 쓰게 한다 (2026-10-20 사용자). 변환은 다듬기만."""
    from apps.blog_types.models import SiteCategory
    from apps.site_templates.models import SiteTemplate
    lines = []
    blogs = Blog.objects.filter(routine=True) if key == "writing" else Blog.objects.filter(platform__in=PLATFORMS.get(key, []))
    blogs = blogs.exclude(status=Blog.Status.HOLD).prefetch_related("checks")
    templates = {t.blog_id: t for t in SiteTemplate.objects.filter(blog__in=blogs)}
    cats = SiteCategory.objects.filter(blog__in=blogs, parent=None).prefetch_related("children").order_by("order", "pk")
    by_blog = {}
    for c in cats:
        by_blog.setdefault(c.blog_id, []).append(c)
    for b in blogs:
        head = f"- {b.name} ({b.address or '주소 없음'}) · {b.content or '컨셉 미정'}"
        head += f" · 하루 {b.daily}편" if b.status == Blog.Status.ACTIVE else f" · {b.get_status_display()}"
        lines.append(head)
        lines += [f"  - 체크: {c.body}" for c in b.checks.all()]
        tpl = templates.get(b.pk)
        if tpl:
            lines += [f"  - {label}: {_one_line(value)}" for label, value in
                      (("말투", tpl.tone), ("구성", tpl.structure), ("꼭 지킬 것", tpl.rules)) if value.strip()]
        all_cats = [(f"{c.name} › {k.name}" if k is not c else c.name, k)
                    for c in by_blog.get(b.pk, []) for k in (c, *c.children.all())]
        if all_cats:
            lines.append("  - 카테고리: " + " · ".join(name for name, _ in all_cats))
            lines += [f"  - 카테고리 {name} 컨셉: {_one_line(k.concept)}" for name, k in all_cats if k.concept.strip()]
    return "\n".join(lines) or "- (해당 사이트 없음)"


def _one_line(text):
    return " ".join((text or "").split())


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
        return _ledger()
    elif key in PLATFORMS:
        from apps.writing import drafts
        if key == "tistory":
            from apps.writing.models import Post
            folder = None
        else:
            from apps.naver_writing.models import Post
            folder = naver_drafts_dir()
        titles += _newest_drafts(drafts.list_drafts(folder))
        titles += list(Post.all_objects.order_by("-created_at").values_list("title", flat=True)[:60])
        titles += list(FeedEntry.objects.filter(blog__platform__in=PLATFORMS[key])
                       .order_by("-published_at").values_list("title", flat=True)[:60])
    seen, out = set(), []
    for t in titles:
        if t and t not in seen:
            seen.add(t)
            out.append(f"- {t}")
    return "\n".join(out[:EXISTING_LINES]) or "- (아직 없음)"


EXISTING_LINES = 40  # 이미 있는 글은 최근 것만 (2026-10-19 사용자: 120줄이 안내문을 키웠다. 더 옛 원고는 원고 폴더에서 찾는다)


def _by_number(items):
    """원고 폴더를 최근 것(T번호 큰 것)부터. 폴더 이름순이면 T100 이 T11 앞에 온다."""
    def number(d):
        digits = re.sub(r"\D", "", d.key.split("_", 1)[0])
        return int(digits) if digits else -1
    return sorted(items, key=number, reverse=True)


def _newest_drafts(items):
    return [d.title for d in _by_number(items)]


LEDGER_DRAFTS = 120  # 장부에 넣는 최근 원고 수
LEDGER_TITLES = 5  # 중분류마다 최근 제목 몇 개
LEDGER_POSTS = 15  # 원고 말고 글 관리·발행 피드의 최근 글
LEDGER_CHARS = 36  # 장부 제목 길이


def _ledger():
    """글쓰기의 '이미 있는 글' = 최근 원고 장부: 중분류마다 소분류(글 틀) 횟수 + 최근 제목.
    작가마다 따로 주제를 고르니 같은 소재·같은 틀이 되풀이됐다 (2026-10-22 사용자).
    주제 기획(writing_topics.md)이 이걸 보고 글 틀을 돌리고 반복을 막는다. 원고 전체 제목은 기획자가 원고 폴더를 Grep 한다."""
    from apps.naver_writing.models import Post as NaverPost
    from apps.writing import drafts
    from apps.writing.models import Post
    items = _by_number(drafts.list_drafts())[:LEDGER_DRAFTS]
    groups = {}
    for d in items:
        parts = [p.strip() for p in d.classification.split(">")] if d.classification else ["분류 없음"]
        parts[0] = re.sub(r"\s*\(.*\)$", "", parts[0])  # '광고 수익 (조회수)' 와 '광고 수익' 을 한 줄로
        types, titles = groups.setdefault(" > ".join(parts[:2]), (Counter(), []))
        if len(parts) > 2:
            types[parts[2]] += 1
        if len(titles) < LEDGER_TITLES:
            short = d.title if len(d.title) <= LEDGER_CHARS else d.title[:LEDGER_CHARS] + "…"
            titles.append(f"{d.code} {short}" + (" [커스텀]" if d.custom else ""))
    lines = [f"최근 원고 {len(items)}편 — 중분류 [글 틀(소분류) 횟수]: 새 것부터 {LEDGER_TITLES}편"]
    for cat, (types, titles) in sorted(groups.items()):
        count = " [" + ", ".join(f"{t} {n}" for t, n in types.most_common()) + "]" if types else ""
        lines.append(f"- {cat}{count}: " + " / ".join(titles))
    drafted = {d.title for d in items}
    others = []
    for model in (Post, NaverPost):
        others += list(model.all_objects.order_by("-created_at", "-pk").values_list("title", flat=True)[:LEDGER_POSTS])
    others += list(FeedEntry.objects.order_by("-published_at").values_list("title", flat=True)[:LEDGER_POSTS])
    others = list(dict.fromkeys(t for t in others if t and t not in drafted))[:LEDGER_POSTS]
    if others:
        lines += ["", "원고 말고 글 관리·발행 피드의 최근 글:"] + [f"- {t}" for t in others]
    return "\n".join(lines)


def _standard(day):
    from apps.daily_ideas.models import SearchStandard
    from apps.daily_ideas.standard import request_text
    standard = SearchStandard.objects.order_by("-version").first()
    if standard is None:
        return "(검색 표준이 아직 없습니다. 일일루틴 › 프롬프트 관리의 검색 표준에서 먼저 저장하세요.)"
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


# 글쓰기 기본 (2026-10-22 사용자): 사이트마다 고정 소재를 두고, 소재가 있는 날만 쓴다 (없으면 절대 쓰지 않는다).
# AI 소식은 일일 분량이 아니라 커스텀 글쓰기의 고정 주제 (memorily).


def _sections():
    from apps.blog_types.models import Section
    return list(Section.objects.prefetch_related("categories__types"))


def default_picks(day):
    """그날의 기본 분류: 글 분류의 모든 소재 한 편씩 = '소재가 있으면 쓸' 후보. 실제로 몇 편 쓸지는 주제 기획이 정한다.
    (day 는 예전 날짜별 무작위의 자리. 지금은 날마다 같다)
    글쓰기 루틴을 끈 사이트(memorily)의 소재는 뺀다 — 그 사이트 글은 고정 주제(AI 소식)나 사용자가 쓴다 (2026-10-23)."""
    off = set(Blog.objects.filter(routine=False).values_list("name", flat=True))
    return {c.sel: 1 for s in _sections() if s.name not in off for c in s.categories.all()}


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
    return _picks_lines(picks, "사용자가 고른 분류" if custom else "기본: 소재가 있는 것만 쓴다, 없으면 건너뛴다")


def _picks_lines(picks, how):
    lines = [f"(총 {sum(picks.values())}편 · {how})"]
    for sel, n in picks.items():
        node, path = _node_path(sel)
        if node is None:
            continue
        line = f"- {path} — {n}편"
        cat = node if node.sel.startswith("c") else (node.category if node.sel.startswith("t") else None)
        if cat is not None and (cat.direction or cat.question):
            line += f" (컨셉: {cat.direction or '-'} / 독자의 질문: {cat.question or '-'})"
        lines.append(line)
        if node.sel.startswith("c"):  # 분류 전체 트리 대신 고른 중분류의 소분류만 (원고의 '분류:' 줄에 쓴다)
            types = [t.name for t in node.types.all()]
            if types:
                lines.append("  - 소분류: " + " · ".join(types))
    return "\n".join(lines)


def _categories_text():
    lines = []
    for s in _sections():
        lines.append(f"- {s.name}")
        for c in s.categories.all():
            lines.append(f"  - {c.code} {c.name}" + (f" — {c.question}" if c.question else ""))
            lines += [f"    - {t.name}" for t in c.types.all()]
    return "\n".join(lines) or "- (분류 없음)"


DATA_TITLES = {"sites": "사이트·체크 · 템플릿 · 카테고리 컨셉", "existing": "이미 있는 글 (겹치지 않게)", "standard": "검색 표준 (최신판)",
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
## 진행 보고
단계가 바뀔 때마다 저장소 폴더에서 아래 명령으로 일일루틴 화면의 실행 이력에 한 줄을 남긴다. 보고가 안 되면 넘어가고 일은 계속한다.

    {cmd}

- 시작: 맨 처음, 오늘 할 일 한 줄
- 진행: 단계가 바뀔 때 (예: "사이트 최근 글 확인", "원고 2/4편 저장")
- 대기: 권한이 없어 실행이 막혀 내 허락이 필요할 때만 (예: "git push 권한 필요"). 보고하고 기다린다. 그 밖의 판단은 묻지 않고 스스로 한다
- 막힘: 접속 차단·자료 없음 등으로 그 단계를 못 할 때. 이유를 적고 할 수 있는 다음 단계로 간다
- 완료: 끝나면 결과 요약 (예: "원고 4편 저장, main push abc1234")
- 실패: 더 진행할 수 없을 때 이유
"""


REPORT_PC = 'workspace/.venv/Scripts/python workspace/manage.py routine_report {key} <상태> "<한 줄>" --date {day}'
REPORT_URL = 'curl -fsS -X POST "{url}" --data-urlencode "status=<상태>" --data-urlencode "step=<한 줄>"'
EXTRA_TITLE = "이번에 할 것 (추가 실행)"
DAILY_TOPICS_TITLE = "매일 쓰는 고정 주제 (전체 실행)"
AHEAD_TITLE = "미리 쓰기 — 예약 발행분"
ALL_ORDER = ("prompt_update", "writing", "daily_ideas")  # 전체 실행 순서 (2026-10-17 사용자). 그 밖의 루틴은 뒤에


def report_url(request, routine, day, via=RoutineRun.Via.RUN):
    """진행 보고를 받을 서버 주소. 보고 토큰이 없으면 "" (PC 의 manage.py routine_report 로)."""
    token = AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)
    if not token:
        return ""
    query = urlencode({"token": token, "day": day.isoformat(), "via": via})
    return request.build_absolute_uri(reverse("routines:report", args=[routine.key])) + "?" + query


def _report(routine, day, report):
    """report: None/False = 붙이지 않음, True/"" = PC 명령, 주소 = 서버로 curl."""
    if report is None or report is False:
        return ""
    if report is True or not report:
        return REPORT.format(cmd=REPORT_PC.format(key=routine.key, day=day))
    return REPORT.format(cmd=REPORT_URL.format(url=report))


def launcher(routine, day, report=None, extra="", tree=False):
    """실행 안내문: 날짜·하루 양 + 읽을 md + 오늘의 자료 (+ 진행 보고).
    extra 는 추가 실행의 내용: '오늘 쓸 분류'(없으면 맨 끝) 자리에 '이번에 할 것'으로 들어간다.
    분류를 고르는 루틴(picks)은 '글 분류 전체'를 빼고 그날 분류만 싣는다 (2026-10-19 사용자: 안내문 줄이기).
    tree=True 면 싣는다 — 분류 없이 코멘트로 시키는 추가 실행은 트리에서 골라야 한다."""
    if extra:
        head = [f"# 일일루틴 · {routine.name} (추가 실행) — {day}", "",
                f"할 일: 하루 분량과 별도로 더 한다 — 아래 '{EXTRA_TITLE}'만큼만."]
    else:
        amount = f"하루 {routine.daily}{routine.unit}"
        if "picks" in routine.data_keys:  # 글쓰기: 그날 분류의 편수 (기본이면 소재 있는 것만)
            picks, custom = day_picks(routine, day)
            amount = f"{sum(picks.values())}{routine.unit}" if custom else f"최대 {sum(picks.values())}{routine.unit}, 소재 있는 것만"
        head = [f"# 일일루틴 · {routine.name} — {day}", "", f"오늘 할 일: {routine.task} — {amount}."]
    lines = head + _ahead(routine, day) + ["아래 md 를 읽고 그대로 따른다.", ""]
    lines.append(f"- `{routine.prompt_doc}` (이 루틴의 프롬프트)" if routine.prompt_doc else "- (프롬프트 md 가 아직 없습니다)")
    keys = routine.data_keys
    if keys:
        lines += ["", "## 오늘의 자료 (서버에서 가져옴)"]
        for k in keys:
            if k == "categories" and "picks" in keys and not tree:
                continue
            if extra and k == "picks":
                lines += ["", f"### {EXTRA_TITLE}", extra]
            else:
                lines += ["", f"### {DATA_TITLES.get(k, k)}", data_text(routine, k, day)]
    if extra and "picks" not in keys:
        lines += ["", f"### {EXTRA_TITLE}", extra]
    if not extra and routine.key == "writing":
        lines += _daily_topics(day)
    return "\n".join(lines).rstrip() + "\n" + _report(routine, day, report)


def _ahead(routine, day):
    """글쓰기를 앞날짜로 돌리면 그날 올릴 글을 미리 쓰는 것 (2026-10-28 사용자: 워크숍 전에 29·30일 글을 써 두고 예약 발행).
    글의 '오늘'·글감은 그 날짜에 맞추고, 그날이 지나야 알 수 있는 글(장 마감 시황 등)은 건너뛴다."""
    today = timezone.localdate()
    if "picks" not in routine.data_keys or day <= today:
        return []
    return [f"## {AHEAD_TITLE}",
            f"오늘은 {today} 이고, 이 실행은 {day} 에 올릴 글을 미리 쓴다 (사용자가 예약 발행한다).",
            f"- 글의 '오늘'은 {day} 다. 기준일·'왜 지금'·남은 날짜·요일·'이번 주말' 같은 말을 {day} 에서 맞게 쓰고, "
            f"원고 표에 `| 발행 예정 | {day} (예약) |` 한 줄을 넣는다.",
            f"- 글감도 {day} 에 읽혀 맞는 것으로 고른다: 그 무렵의 일정·마감·개장·계절 글, 날짜를 타지 않는 정보 글.",
            f"- {day} 가 지나야 알 수 있는 글(그날 장 마감 시황, 그날 발표·결과, 실시간 순위·날씨)은 쓰지 않는다. "
            "그 분류는 '미리 못 씀' 한 줄로 보고하고 넘어간다.",
            f"- 숫자·일정은 지금 확인하고, 확인한 날은 실제 날짜({today.month}월 {today.day}일 확인)로 적는다.", ""]


def _daily_topics(day):
    """전체 실행(글쓰기)에 매일 1편씩 붙는 고정 주제 (FixedTopic.daily, 2026-10-23 사용자: AI 소식). 기획 없이 작가에게 바로."""
    from .models import FixedTopic
    from .topics import topic_text
    topics = list(FixedTopic.objects.filter(daily=True).select_related("category__section"))
    if not topics:
        return []
    lines = ["", f"### {DAILY_TOPICS_TITLE}",
             "일일 분량과 함께 쓴다. 기획자에게 넘기지 않고 작가에게 바로 맡긴다 (T번호는 일일 원고 다음). 글감이 없으면 원고 없이 보고만."]
    for i, t in enumerate(topics, start=1):
        lines += ["", f"#### {i}. {t.name}", topic_text(t, day, 1)]
    return lines


def restore_prompt(version, day, report=None):
    """좋았던 버전으로 되돌리는 안내문: AI 가 프롬프트 md 를 그 버전 내용으로 고쳐 main 에 올린다."""
    routine = version.routine
    lines = [f"# 일일루틴 프롬프트 되돌리기 · {routine.name} v{version.number} — {day}", "",
             f"대상 프롬프트: `{routine.prompt_doc}`", "", "## 할 일",
             f"1. 대상 프롬프트를 아래 'v{version.number} 내용'으로 되돌린다 (사용자가 좋았던 버전으로 고름).",
             "2. 맨 아래 '평가에서 배운 점'에 되돌린 날짜와 이유를 한 줄 더한다.",
             f"3. main 에 커밋·push 한다. 커밋 메시지: `prompt: {routine.name} v{version.number} 로 되돌림`."]
    lines += ["", f"## v{version.number} 내용", "", version.content]
    return "\n".join(lines).rstrip() + "\n" + _report(routine, day, report)


# ---- 프롬프트가 보는 것: 프롬프트 md, 그 안에서 읽게 하는 md, 오늘의 자료

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
    """[{kind, label, rel, ok}] — 프롬프트 md · 읽는 md · 오늘의 자료."""
    out = [{"kind": "프롬프트", "label": routine.prompt_doc or "(프롬프트 md 없음)",
            "rel": _md_path(routine.prompt_doc) if routine.prompt_doc else None}]
    seen = {routine.prompt_doc}
    for rel in _reads(_read(routine.prompt_doc)):
        if rel not in seen:
            seen.add(rel)
            out.append({"kind": "읽는 md", "label": rel, "rel": _md_path(rel)})
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


def _day(request):
    try:
        return date.fromisoformat(request.POST.get("day", ""))
    except ValueError:
        return timezone.localdate()


def _in_all_order(routines):
    return sorted(routines, key=lambda r: ALL_ORDER.index(r.key) if r.key in ALL_ORDER else len(ALL_ORDER))


ALL_PART = "<!-- 일일루틴 루틴: {key} -->"  # 전체 실행 안내문의 루틴 경계 (local_run.split_all 이 나눈다)


def all_prompt(routines, day, report_for=lambda r: True):
    """전체 실행 안내문: ALL_ORDER 순서로 각 안내문(진행 보고 포함)을 이어 붙인다.
    PC 는 이것을 루틴마다 나눠 새 터미널에서 차례로 돌린다 (local_run.start). 2026-10-19: 한 대화로 이으면
    답할 때마다 앞 루틴의 대화까지 다시 읽어 토큰이 크게 늘었다."""
    routines = _in_all_order(routines)
    head = [f"# 일일루틴 전체 실행 — {day}", "",
            "아래 루틴을 위에서부터 차례로 끝까지 진행한다. PC 에서는 루틴마다 새 터미널이 열리고, 앞 루틴이 끝나면 다음 루틴이 시작된다.",
            "- 앞 루틴이 고친 프롬프트 md 는 다음 루틴이 새로 읽는다.",
            "- 한 루틴이 막히면 막힘으로 보고하고 끝낸다. 내가 할 일이 생기면 대기로 보고하고 기다린다.",
            "- 순서: " + " → ".join(f"{i}. {r.name}" for i, r in enumerate(routines, start=1)), ""]
    parts = ["\n".join(head)]
    for r in routines:
        parts.append(f"\n{ALL_PART.format(key=r.key)}\n" + launcher(r, day, report=report_for(r)))
    return "\n".join(parts)


# ---- 일일루틴 리스트

def index(request):
    _nav(request)
    try:  # AI 가 남긴 분류 변경 파일을 먼저 반영한다 (일일루틴/분류변경)
        from apps.blog_types import changes
        changes.sync()
    except Exception:  # 분류 변경이 잘못돼도 화면은 뜬다 (기록은 관리화면)
        pass
    try:  # 루틴이 새로 쓴 원고를 임시글으로 — 글쓰기 결과 수는 글을 센다 (2026-10-20: 글 관리를 열기 전엔 0 이었다)
        from apps.writing.views import auto_import_drafts
        auto_import_drafts()
    except Exception:  # 원고 하나가 잘못돼도 화면은 뜬다
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
        open_goal = False  # 글쓰기 기본(소재 있는 것만)은 정해진 목표가 없다 — 한 편이라도 쓰면 완료
        if "picks" in r.data_keys and mode == "day":  # 그날 고른 편수가 목표
            picks, custom = day_picks(r, sel)
            r.target, open_goal = (sum(picks.values()), False) if custom else ("", True)
        if start > today and not r.result:  # 앞날짜는 비워 두되, 미리 쓴 글이 있으면 그 날 결과로 보인다 (2026-10-28 사용자)
            r.state = ""
        elif open_goal:
            r.state = "done" if r.result else "todo"
        else:
            r.state = ("done" if r.result >= r.target else "todo") if r.target else ""
        r.auto = auto[r.pk][sel]
        r.fixed = (r.pk, sel) in fixed
        r.url = reverse(r.url_name)
        r.prompt = launcher(r, run_day, report=report_url(request, r, run_day))
    runs = (RoutineRun.objects.select_related("routine")  # 실행 이력: 모든 루틴, 이 기간 + 끝나지 않은 것
            .filter(Q(day__range=(start, end)) | Q(status__in=[RoutineRun.Status.RUNNING, RoutineRun.Status.WAITING,
                                                                 RoutineRun.Status.BLOCKED]))[:50])
    from . import topics as topic_mod  # 글쓰기 줄 아래로 펼치는 커스텀 글쓰기 (사이트별 소재·고정 주제)
    topic_groups = topic_mod.groups()
    from .results import counts, writing_results  # 실행 이력 아래 '글쓰기 결과' + 예정(코스피 15:30 전) 뱃지
    results = writing_results(run_day)
    planned = {row["sel"]: row["reason"] for row in results if row["state"] == "planned" and row["sel"]}
    for g in topic_groups:
        for c in g["cats"]:
            c.planned = planned.get(c.sel)
    for r in routines:
        r.planned = len(planned) if r.key == topic_mod.WRITING_KEY else 0
    return render(request, "routines/index.html", {
        "results": results, "result_counts": counts(results),
        "page_title": "일일루틴",
        "topic_groups": topic_groups, "topic_count": sum(g["count"] for g in topic_groups),
        "writing_key": topic_mod.WRITING_KEY,
        "bar": period.bar(mode, sel, today, state),
        "mode": mode,
        "day": sel,
        "run_day": run_day,
        "routines": routines,
        "done_total": sum(1 for r in routines if r.state == "done"),
        "runs": runs,
        "has_open_run": any(run.is_open for run in runs),
        "all_prompt": _with_feeds(request, all_prompt(routines, run_day, lambda r: report_url(request, r, run_day))) if routines else "",
        "all_keys": ",".join(r.key for r in _in_all_order(routines)),
        "on_server": settings.IS_SERVER,
        "keep": request.get_full_path().partition("?")[2],
    })


def _with_feeds(request, text):
    """전체 실행 안내문 첫 줄 뒤에 발행 확인(모니터링)을 숨겨 둔다. PC 가 루틴 창을 연 뒤 RSS 를 읽어 서버로 보낸다
    (local_run.FEEDS_MARK, 2026-10-22 사용자: 발행 완료 자동 처리). 루틴 안내문(루틴마다 나눈 것)에는 들어가지 않는다."""
    from apps.blog_ops.views import check_text
    feeds = check_text(request)
    if not text or not feeds:
        return text
    head, _, rest = text.partition("\n")
    return f"{head}\n<!-- 발행 확인 {feeds.split(chr(10), 1)[1].strip()} -->\n{rest}"


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
    """좋았던 버전으로 되돌리는 안내문 ('실행'으로 PC 터미널에서)."""
    _nav(request, "routine_prompts")
    v = get_object_or_404(PromptVersion, pk=pk)
    today = timezone.localdate()
    return render(request, "routines/restore.html", {
        "page_title": f"{v.routine.name} v{v.number} 로 되돌리기", "version": v, "routine": v.routine, "today": today,
        "on_server": settings.IS_SERVER,
        "prompt": restore_prompt(v, today, report=report_url(request, v.routine, today))})


def _report_form(request):
    """보고 본문 {status, step}. Windows 의 curl 은 --data-urlencode 의 한글을 cp949 로 보낸다
    (2026-10-20: '시작'이 깨져 보고가 모두 400 으로 거절됐다) → UTF-8 로 안 읽히면 cp949 로 읽는다."""
    if request.content_type != "application/x-www-form-urlencoded":
        return request.POST
    raw = request.body.decode("ascii", "replace")
    for encoding in ("utf-8", "cp949"):
        try:
            return {k: v[0] for k, v in parse_qs(raw, encoding=encoding, errors="strict").items()}
        except UnicodeDecodeError:
            continue
    return {k: v[0] for k, v in parse_qs(raw, encoding="utf-8", errors="replace").items()}


@csrf_exempt
@login_not_required
@require_POST
def report_api(request, key):
    """진행 보고 한 줄 ('실행'·'전체 실행'·'추가 실행' 터미널의 claude 가 curl 로 보낸다). 토큰이 맞아야 남긴다."""
    token = AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)
    if not token or not hmac.compare_digest(request.GET.get("token", ""), token):
        return HttpResponseForbidden("token")
    routine = get_object_or_404(Routine, key=key)
    form = _report_form(request)
    word = form.get("status", "").strip()
    if word not in RoutineRun.WORDS:
        return HttpResponseBadRequest("status: " + " · ".join(RoutineRun.WORDS))
    try:
        day = date.fromisoformat(request.GET.get("day", ""))
    except ValueError:
        day = timezone.localdate()
    via = request.GET.get("via") if request.GET.get("via") in RoutineRun.Via.values else RoutineRun.Via.RUN
    run = RoutineRun.record(routine, day, word, form.get("step", "").strip()[:500], via)
    return HttpResponse(f"ok {routine.key} {day} {run.status}", content_type="text/plain; charset=utf-8")


@require_POST
def extra(request, pk):
    """하루 분량과 따로 더 하는 안내문 (JSON). mode=comment: 커스텀 글쓰기의 자유 글쓰기 코멘트. mode=count: 개수 + 방향.
    화면이 받아 '실행'처럼 PC 터미널을 연다. (고른 소재·고정 주제는 topics.run)"""
    routine = get_object_or_404(Routine, pk=pk)
    day = _day(request)
    mode = request.POST.get("mode")
    if mode == "count":
        raw = request.POST.get("count", "").strip()
        if not raw.isdigit() or not 1 <= int(raw) <= 30:
            return JsonResponse({"error": "개수는 1~30 으로 넣으세요."}, status=400)
        comment = request.POST.get("comment", "").strip()[:2000]
        body = f"{int(raw)}{routine.unit} 더 한다."
        if comment:
            body += f"\n방향 (사용자 코멘트): {comment}"
    elif mode == "comment":
        comment = request.POST.get("comment", "").strip()[:2000]
        if not comment:
            return JsonResponse({"error": "무엇을 몇 편 쓸지 코멘트를 적으세요."}, status=400)
        body = (f"사용자 코멘트: {comment}\n"
                "- 편수·주제·분류는 코멘트를 따른다. 분류가 적혀 있지 않으면 '글 분류 전체'에서 주제에 맞는 중분류를 고른다.\n"
                "- 편수가 없으면 1편.")
    else:
        return JsonResponse({"error": "mode 는 comment 또는 count 입니다."}, status=400)
    return JsonResponse({"prompt": launcher(routine, day, report=report_url(request, routine, day), extra=body,
                                            tree=mode == "comment")})


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
    return render(request, "core/confirm_delete.html", {
        "page_title": "삭제", "kind_label": "루틴", "object_label": routine.name, "cancel_url": reverse("routines:edit", args=[routine.pk]),
        "crumbs": [("일일루틴", reverse("routines:index")), ("프롬프트 관리", reverse("routines:prompts"))]})
