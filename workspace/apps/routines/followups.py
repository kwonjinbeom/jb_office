"""이어서 할 일 (2026-10-31 사용자): 글쓰기·변환 터미널이 끝까지 못 하고 끝났을 때, 뒤이어 할 일을 남기고 이력을 보는 화면.

버튼으로 글쓰기·변환을 누르면 PC 에 claude 터미널이 열렸다 닫혀서, 어디서 멈췄는지 알 수 없었다.
- 남기는 길 둘:
  ① claude 가 끝낼 때 못 한 일을 JSON 파일로 써서 보고 주소(api_new)로 보낸다 — 모든 안내문 끝의 '끝내지 못한 일'(instruction).
     보고 토큰이 없으면 PC 의 `manage.py routine_followup new` 로 PC DB 에.
  ② 화면의 '확인이 필요한 것': 실행 이력 중 실패·막힘, 또는 STALE_HOURS 넘게 소식 없는 진행·대기 → '남은 일로' 올린다.
     일일아이디어는 빼고 본다 (2026-10-31 사용자: 의미 없다).
- 다시 확인 (2026-10-31 사용자): 막힌 게 아니라 정보가 아직 안 나와 그날 다시 찾아야 하는 일 (check_on). 예: 11/1 0시에 공개되는
  올영 블프 쿠폰·본 행사 혜택. '확인이 필요한 것' 칸에 그날까지 '기다림', 그날부터 '확인할 때'로 보이고 이어서 하기로 확인한다.
- 이어서 하기: 남은 일 · 멈춘 까닭 · 이어서 할 일 · 그때 실행 기록을 안내문으로 만들어 PC 터미널 claude 를 연다 (local_run kind followup).
  그 claude 가 끝에 api_report 로 '완료'를 보내면 완료, '실패'면 남음으로 돌아오고 이어서 할 일이 고쳐진다.
JSON 으로 받는 까닭: Windows curl 은 명령줄 한글을 cp949 로 보낸다 (2026-10-20). 파일은 UTF-8 그대로 간다.
"""
import hmac
import json
from datetime import date, timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting

from .models import FollowUp, Routine, RoutineRun

NAV = "routine_followups"
STALE_HOURS = 3  # 진행·대기인데 이만큼 소식이 없으면 '멈춤?'
QUIET_ROUTINES = ["daily_ideas"]  # '확인이 필요한 것'에 올리지 않는 루틴 (2026-10-31 사용자: 일일아이디어는 의미 없다)
RUN_DAYS = 14  # '확인이 필요한 실행'으로 볼 기간
DONE_WORDS = {"완료": FollowUp.Status.DONE, "실패": FollowUp.Status.OPEN, "막힘": FollowUp.Status.OPEN}
HEAD = "# 일일루틴 이어서 하기"  # local_run.PROMPT_HEAD('# 일일루틴')로 시작해야 PC 가 받는다
JSON_FILE = "workspace/.routine/followup.json"
PC_PYTHON = "workspace/.venv/Scripts/python workspace/manage.py routine_followup"


# ---- 안내문에 붙는 '끝내지 못한 일'

INSTRUCTION = """
## 끝내지 못한 일 (이어서 할 일)
맨 마지막 보고 다음에: 아래 둘 중 하나라도 있으면 '이어서 할 일'에 남긴다. 둘 다 없으면 남기지 않는다.
- 끝내지 못한 것: 막힘 · 실패 · 권한 · 확인 못 해 건너뛴 것.
- 나중에 다시 찾아야 할 것: 막힌 게 아니라 정보가 아직 공개 전이라 그날 다시 확인해야 하는 것 (예: 11월 1일 0시에 열리는 본 행사 할인·쿠폰·상품, 다음 주에 나오는 발표). 원고에 '공개 전'·'앱에서 확인'으로 남긴 자리가 있으면 꼭 남긴다.
1. Write 도구로 `{file}` 에 UTF-8 JSON 을 쓴다. 한 일마다 한 건, 여럿이면 목록 `[{{…}}, {{…}}]`:
   `{{"title": "무엇을 못 했나 한 줄", "why": "왜 멈췄나 한 줄", "next": "이어서 할 일 1~5줄"}}`
   나중에 다시 찾아야 할 것은 `"check_on": "YYYY-MM-DD"` (다시 볼 날)을 더한다.
   - title 예: "T226 순천 당일치기 원고 — 네이버 지도 장소 번호를 못 찾음" · "T236 올영 블프 — 11/1 본 행사 쿠폰·할인 공개 확인"
   - next 는 다음 claude 가 이것만 보고 이어서 할 수 있게: 어디까지 했나(원고 폴더·파일) · 무엇을 하면 끝나나 · 무엇으로 확인하나 (다시 확인이면 어디서 무엇을 보고, 새로 알릴 게 있으면 원고를 고칠지 새 글을 쓸지)
2. 아래 명령을 그대로 실행한다. 보내기가 안 되면 넘어간다.

    {cmd}
"""


def _url(request, name, args=(), **query):
    token = AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)
    if not token or request is None:
        return ""
    return request.build_absolute_uri(reverse(name, args=args)) + "?" + urlencode({"token": token, **query})


def new_url(request, source, day, key=""):
    """'끝내지 못한 일'을 받는 서버 주소 (토큰이 없으면 "")."""
    return _url(request, "routines:followup_new", source=source, day=day.isoformat(), key=key)


def instruction(url, source, day, key=""):
    """안내문 끝에 붙이는 '끝내지 못한 일'. url 이 없으면 PC 명령으로."""
    if url:
        cmd = f'curl -fsS -X POST "{url}" -H "Content-Type: application/json; charset=utf-8" --data-binary "@{JSON_FILE}"'
    else:
        cmd = f"{PC_PYTHON} new {JSON_FILE} --source {source} --date {day}" + (f" --key {key}" if key else "")
    return INSTRUCTION.format(file=JSON_FILE, cmd=cmd)


def instruction_from_report(report, routine, day):
    """루틴 안내문(views._report)용: 진행 보고 주소에서 같은 서버·토큰으로 '끝내지 못한 일' 주소를 만든다."""
    source = FollowUp.Source.WRITING if routine.key == "writing" else FollowUp.Source.ROUTINE
    if isinstance(report, str) and report:
        base, _, query = report.partition("?")
        params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
        root = base.split("/routines/report/")[0]
        url = f"{root}{reverse('routines:followup_new')}?" + urlencode(
            {"token": params.get("token", ""), "source": source, "day": day.isoformat(), "key": routine.key})
        return instruction(url, source, day, routine.key)
    return instruction("", source, day, routine.key)


# ---- 받기 (claude 가 보낸다)

def _items(raw):
    data = json.loads(raw)
    items = data if isinstance(data, list) else [data]
    return [i for i in items if isinstance(i, dict) and str(i.get("title", "")).strip()]


def _day(raw):
    try:
        return date.fromisoformat(raw or "")
    except ValueError:
        return timezone.localdate()


def _check_on(raw):
    try:
        return date.fromisoformat(str(raw or "").strip()[:10])
    except ValueError:
        return None


def add_items(items, source, day, key="", run=None):
    """받은 [{title, why, next}] 를 남긴다. 같은 날 · 같은 제목의 남은 일이 있으면 그것을 고친다. 남긴 것을 돌려준다."""
    source = source if source in FollowUp.Source.values else FollowUp.Source.OTHER
    routine = Routine.objects.filter(key=key).first() if key else None
    if run is None and routine is not None:
        run = RoutineRun.objects.filter(routine=routine, day=day).first()
    out = []
    for item in items:
        title = " ".join(str(item["title"]).split())[:200]
        why = str(item.get("why", "")).strip()[:2000]
        nxt = str(item.get("next", "")).strip()[:4000]
        check_on = _check_on(item.get("check_on"))
        fu = FollowUp.objects.filter(title=title, day=day, status__in=[FollowUp.Status.OPEN, FollowUp.Status.RUNNING]).first()
        if fu is None:
            fu = FollowUp(title=title, day=day, source=source, routine=routine, run=run)
        fu.why, fu.next_steps = why or fu.why, nxt or fu.next_steps
        fu.check_on = check_on or fu.check_on
        fu.note(f"터미널이 남김 · {fu.check_on:%m-%d} 다시 확인" if fu.check_on else "터미널이 남김", FollowUp.Status.OPEN)
        out.append(fu)
    return out


def _token_ok(request):
    token = AppSetting.get(ROUTINE_BRIEF_TOKEN_KEY)
    return bool(token) and hmac.compare_digest(request.GET.get("token", ""), token)


@csrf_exempt
@login_not_required
@require_POST
def api_new(request):
    """'끝내지 못한 일' 받기. 본문은 UTF-8 JSON (한 건 또는 목록). ?token · source · day · key."""
    if not _token_ok(request):
        return HttpResponseForbidden("token")
    try:
        items = _items(request.body.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponseBadRequest("json: {\"title\", \"why\", \"next\"}")
    if not items:
        return HttpResponseBadRequest("title 이 없습니다")
    saved = add_items(items, request.GET.get("source", ""), _day(request.GET.get("day")), request.GET.get("key", ""))
    return HttpResponse(f"ok {len(saved)} " + " ".join(f"#{f.pk}" for f in saved), content_type="text/plain; charset=utf-8")


def apply_report(fu, data):
    """이어서 하기 터미널의 끝 보고 {status: 완료|실패|막힘, note, next}."""
    word = str(data.get("status", "")).strip()
    if word not in DONE_WORDS:
        raise ValueError("status: " + " · ".join(DONE_WORDS))
    nxt = str(data.get("next", "")).strip()
    if nxt:
        fu.next_steps = nxt[:4000]
    fu.note(str(data.get("note", "")).strip()[:500] or word, DONE_WORDS[word])


@csrf_exempt
@login_not_required
@require_POST
def api_report(request, pk):
    if not _token_ok(request):
        return HttpResponseForbidden("token")
    fu = get_object_or_404(FollowUp, pk=pk)
    try:
        apply_report(fu, json.loads(request.body.decode("utf-8-sig")))
    except (ValueError, UnicodeDecodeError) as e:
        return HttpResponseBadRequest(str(e))
    return HttpResponse(f"ok #{fu.pk} {fu.status}", content_type="text/plain; charset=utf-8")


# ---- 이어서 하기 안내문

GUIDES = {
    "writing": "글쓰기면 `일일루틴/프롬프트/writing.md` 와 그 사이트 파일(writing_site_<사이트>.md)을 먼저 읽고 그 규칙대로 쓴다. 원고 폴더는 `콘텐츠/블로그_카페/포스팅자동화/원고`.",
    "convert": "변환이면 글 관리의 그 글을 다시 '변환'하거나, 지난 변환 안내문(`workspace/.routine/cv-*.md`)의 그 글 부분을 보고 같은 방법으로 보낸다.",
    "anime": "애니면 `콘텐츠/블로그_카페/memorily_티스토리/애니총정리/00_작업순서.md` 를 먼저 읽는다.",
}
REPORT_DONE = """
## 끝나면
Write 도구로 `{file}` 에 UTF-8 JSON 을 쓰고 아래 명령을 실행한다.
- 다 했으면 `{{"status": "완료", "note": "무엇을 했나 한 줄 (예: 원고 저장, main push abc1234)"}}`
- 또 못 했으면 `{{"status": "실패", "note": "왜 한 줄", "next": "남은 것 1~5줄 (지금 기준으로 고쳐서)"}}`

    {cmd}
"""


def resume_prompt(fu, request=None):
    today = timezone.localdate()
    url = _url(request, "routines:followup_report", args=[fu.pk])
    file = f"workspace/.routine/followup-{fu.pk}.json"
    cmd = (f'curl -fsS -X POST "{url}" -H "Content-Type: application/json; charset=utf-8" --data-binary "@{file}"' if url
           else f"{PC_PYTHON} report {fu.pk} {file}")
    lead = (f"지난번 {fu.get_source_display()} ({fu.day}) 실행이 {fu.check_on} 에 다시 확인하기로 남긴 일이다. "
            "그때 공개 전이던 정보를 지금 공식 출처로 다시 찾고, 새로 알릴 게 있으면 '이어서 할 일'대로 원고를 고치거나 새 글을 쓴다. "
            "아직도 안 나왔으면 '실패'로 보고하고 next 에 다시 볼 날을 적는다."
            if fu.check_on else f"지난번 {fu.get_source_display()} ({fu.day}) 실행이 끝내지 못한 일을 이어서 한다.")
    lines = [f"{HEAD} · {fu.title} — {today}", "",
             lead + " 사용자에게 묻지 않고 스스로 판단해 끝까지 한다.",
             "먼저 `AGENTS.md` 를 읽는다. 그사이 사용자가 직접 끝냈을 수 있으니 원고 폴더 · git 기록으로 이미 된 것인지부터 본다 (됐으면 바로 '완료').",
             "", "## 남은 일", fu.title, "", "## 다시 확인하는 까닭" if fu.check_on else "## 멈춘 까닭", fu.why or "(적힌 것 없음)",
             "", "## 이어서 할 일", fu.next_steps or "(적힌 것 없음 — 아래 실행 기록과 원고 폴더를 보고 끝나지 않은 단계부터)"]
    if fu.run_id and fu.run.log:
        lines += ["", f"## 그때 실행 기록 ({fu.run.routine.name} · {fu.run.day})", "```", fu.run.log, "```"]
    if fu.log:
        lines += ["", "## 이 남은 일의 기록", "```", fu.log, "```"]
    guide = GUIDES.get(fu.source)
    if guide:
        lines += ["", "## 참고", f"- {guide}", "- 결과는 main 에 올린다 (git pull --rebase 뒤 push)."]
    return "\n".join(lines).rstrip() + "\n" + REPORT_DONE.format(file=file, cmd=cmd)


@require_POST
def resume(request, pk):
    """이어서 하기 안내문 (JSON). 화면이 받아 PC 터미널 claude 를 연다 (local_run kind followup)."""
    fu = get_object_or_404(FollowUp, pk=pk)
    text = resume_prompt(fu, request)
    fu.note("이어서 하기 · PC 터미널을 열었습니다", FollowUp.Status.RUNNING)
    return JsonResponse({"prompt": text, "key": f"fu{fu.pk}", "day": timezone.localdate().isoformat(),
                         "name": f"이어서 하기 #{fu.pk}"})


# ---- 화면

def stale_runs(now=None):
    """확인이 필요한 실행: 최근 RUN_DAYS 일의 실패 · 막힘, 또는 STALE_HOURS 넘게 소식 없는 진행 · 대기. 남은 일로 올린 것은 뺀다."""
    now = now or timezone.now()
    since = timezone.localdate() - timedelta(days=RUN_DAYS)
    quiet = now - timedelta(hours=STALE_HOURS)
    runs = (RoutineRun.objects.select_related("routine").filter(day__gte=since)
            .filter(Q(status__in=[RoutineRun.Status.FAILED, RoutineRun.Status.BLOCKED])
                    | Q(status__in=[RoutineRun.Status.RUNNING, RoutineRun.Status.WAITING], updated_at__lt=quiet))
            .exclude(routine__key__in=QUIET_ROUTINES)
            .annotate(n=Count("followups")).filter(n=0).order_by("-updated_at"))
    out = list(runs[:30])
    for r in out:
        r.why = "소식 없음 (터미널이 닫혔을 수 있어요)" if r.status in (RoutineRun.Status.RUNNING, RoutineRun.Status.WAITING) else r.get_status_display()
    return out


def page(request):
    request.nav_key = NAV
    tab = request.GET.get("t", "open")
    qs = FollowUp.objects.select_related("routine", "run__routine")
    live = qs.filter(status__in=[FollowUp.Status.OPEN, FollowUp.Status.RUNNING])
    # 다시 확인할 일은 아래 '확인이 필요한 것' 칸에 (다시 볼 날 순)
    rechecks = list(live.filter(check_on__isnull=False).order_by("check_on", "pk"))
    counts = {"open": live.filter(check_on__isnull=True).count(), "recheck": len(rechecks),
              "done": qs.filter(status__in=[FollowUp.Status.DONE, FollowUp.Status.DROPPED]).count()}
    if tab == "open":
        items = live.filter(check_on__isnull=True)
    elif tab == "done":
        items = qs.filter(status__in=[FollowUp.Status.DONE, FollowUp.Status.DROPPED])
    else:
        tab, items = "all", qs
    quiet = timezone.now() - timedelta(hours=STALE_HOURS)
    items = list(items[:100])
    for f in items + rechecks:
        f.stuck = f.status == FollowUp.Status.RUNNING and f.updated_at < quiet
        f.first_next = (f.next_steps.strip().splitlines() or [""])[0]
    runs = stale_runs() if tab != "done" else []
    rechecks = rechecks if tab != "done" else []
    return render(request, "routines/followups.html", {
        "page_title": "이어서 할 일", "tab": tab, "items": items, "counts": counts,
        "runs": runs, "rechecks": rechecks, "check_count": len(runs) + len(rechecks),
        "stale_hours": STALE_HOURS, "run_days": RUN_DAYS,
        "today": timezone.localdate(), "on_server": settings.IS_SERVER,
        "sources": FollowUp.Source.choices,
    })


def _back(request):
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else reverse("routines:followups"))


@require_POST
def add(request):
    title = " ".join(request.POST.get("title", "").split())[:200]
    if not title:
        messages.warning(request, "남은 일을 한 줄 적으세요.")
        return _back(request)
    fu = FollowUp(title=title, day=_day(request.POST.get("day")), source=request.POST.get("source") or FollowUp.Source.OTHER,
                  next_steps=request.POST.get("next_steps", "").strip()[:4000], check_on=_check_on(request.POST.get("check_on")))
    fu.note("직접 적음", FollowUp.Status.OPEN)
    return _back(request)


@require_POST
def save(request, pk):
    fu = get_object_or_404(FollowUp, pk=pk)
    title = " ".join(request.POST.get("title", "").split())[:200]
    if title:
        fu.title = title
    fu.why = request.POST.get("why", "").strip()[:2000]
    fu.next_steps = request.POST.get("next_steps", "").strip()[:4000]
    if "check_on" in request.POST:
        fu.check_on = _check_on(request.POST.get("check_on"))
    fu.note("고침")
    return _back(request)


ACTIONS = {"done": (FollowUp.Status.DONE, "완료로 (사용자)"), "drop": (FollowUp.Status.DROPPED, "안 하기로 (사용자)"),
           "open": (FollowUp.Status.OPEN, "다시 남음으로 (사용자)")}


@require_POST
def mark(request, pk, action):
    fu = get_object_or_404(FollowUp, pk=pk)
    if action in ACTIONS:
        status, message = ACTIONS[action]
        fu.note(message, status)
    return _back(request)


@require_POST
def promote(request, pk):
    """확인이 필요한 실행 → 남은 일. 실행 기록은 이어서 하기 안내문에 함께 간다."""
    run = get_object_or_404(RoutineRun.objects.select_related("routine"), pk=pk)
    source = FollowUp.Source.WRITING if run.routine.key == "writing" else FollowUp.Source.ROUTINE
    fu = FollowUp(title=f"{run.routine.name} {run.day:%m-%d} — {run.step or run.get_status_display()}"[:200], day=run.day,
                  source=source, routine=run.routine, run=run, why=run.step or run.get_status_display(),
                  next_steps="실행 기록(이어서 하기 안내문에 붙는다)을 보고, 끝나지 않은 단계부터 이어서 한다.")
    fu.note("실행 이력에서 올림", FollowUp.Status.OPEN)
    return _back(request)


@require_POST
def close_run(request, pk):
    """확인이 필요한 실행을 '괜찮음'으로 닫는다 (실행 이력에 한 줄 남기고 완료로)."""
    run = get_object_or_404(RoutineRun, pk=pk)
    run.report(RoutineRun.Status.DONE, "사용자가 확인하고 닫음 (이어서 할 일)", timezone.localtime())
    return _back(request)
