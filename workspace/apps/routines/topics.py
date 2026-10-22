"""커스텀 글쓰기: 내가 골라서 더 쓰는 글쓰기 (2026-10-21 사용자, 2026-10-23 사이트별로 다시 정리).

- 사이트마다 두 가지 줄이 있다 (2026-10-23 사용자: 일일루틴 글쓰기가 쓰는 소재를 여기서도 골라 더 쓰고 싶다).
  ① 소재: 글 분류의 '사이트 > 고정 소재' 그대로 (blog_types.Category). 일일루틴 글쓰기가 매일 보는 그 소재다.
  ② 고정 주제(FixedTopic): 주제·지침을 따로 적어 둔 것 (공모주 일정 · AI 소식 등). 사이트가 같으면 그 사이트 아래에.
- 줄 앞 체크 + 편수(기본 1) → 위의 '실행': 고른 것을 한 터미널에서 한꺼번에 쓴다. 메인 claude 는 글쓰기 md 대로
  소재는 보조 기획자에게, 고정 주제는 바로 보조 작가에게 나눠 준다 (서브 원고).
- 왼쪽 자유 글쓰기: 쓰고 싶은 걸 자유롭게 적고 '글쓰기' (views.extra mode=comment).
- 일일루틴 화면의 글쓰기 줄을 누르면 같은 목록이 그 아래로 펼쳐지고, 줄마다 '실행'(1편)이 있다.
- 예전의 주 단위 발행 점(TopicWeek)·주당 편수는 화면에서 뺐다 (데이터는 남겨 둔다).
"""
import re

from django.contrib import messages
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog_types import sites

from .models import FixedTopic, Routine

WRITING_KEY = "writing"
MAX_EACH = 10  # 한 줄 최대 편수


def topic_text(topic, today, n=1):
    """고정 주제 한 줄이 '이번에 할 것'에 들어갈 내용"""
    lines = [
        f"고정 주제: {topic.name} — {n}편.",
        "- 다루는 기간·지역은 아래 지침을 따르고 (예: 공모주는 앞으로 한 달·분기), 지침에 없으면 오늘 기준. 일정·숫자는 공식 출처에서 오늘 다시 확인한다.",
        f"- 사이트: {topic.site or '주제에 맞는 사이트를 고른다'}",
        "- 같은 주제의 지난 원고(원고 폴더의 `고정주제:` 줄)를 먼저 보고, 겹치는 건 바뀐 것만 짚고 새 내용 위주로 쓴다.",
        f"- 글감부터 본다 (2026-10-22 사용자): 오늘({today:%Y-%m-%d}) 기준으로 새로 쓸 게 없으면 원고를 만들지 않는다 — 폴더·원고.md 없이"
        " 진행 보고에 '글감 없음 · 이유 한 줄'만 남기고 끝낸다. 억지로 채운 글은 품질만 떨어뜨린다.",
        "- 날짜가 지난 것은 쓰지 않는다: 접수·마감·청약·상장·발표일이 오늘 이전에 끝난 항목은 빼고, 쓰기 직전에 항목마다 날짜를 오늘과 다시 대조한다."
        " 남는 게 지난 원고와 같은 항목뿐이고 바뀐 게 없으면 글감 없음이다.",
        f"- 원고 제작 정보 맨 위 `사이트:` · `분류:` 줄 아래에 `고정주제: {topic.name}` 줄을 넣는다.",
        "- 분류는 '글 분류 전체'에서 주제에 맞는 것을 고른다.",
    ]
    if topic.note.strip():
        lines += ["", "이 주제의 지침 (사용자):", topic.note.strip()]
    return "\n".join(lines)


def run_text(cats, topics, today):
    """고른 소재 [(Category, 편수)] · 고정 주제 [(FixedTopic, 편수)] → '이번에 할 것'. 한 터미널에서 서브 원고로 한꺼번에."""
    from .views import _picks_lines
    total = sum(n for _, n in cats) + sum(n for _, n in topics)
    lines = [f"커스텀 글쓰기 (사용자가 고른 것, 최대 {total}편): 하루 분량과 따로, 아래 것만 쓴다. "
             "메인은 글쓰기 md 의 '나눠 쓰기'대로 나눠 주기만 하고, 원고는 1편마다 보조 작가가 쓴다.",
             "- 원고 제작 정보 맨 위 `사이트:` · `분류:` 줄 아래에 소재 원고는 `커스텀: 커스텀 글쓰기`, 고정 주제 원고는 `고정주제: <주제>` 줄을 넣는다.",
             "- 글감이 없는 것은 원고 없이 진행 보고에 '글감 없음 · 이유 한 줄'만 남기고 다음으로 간다."]
    if cats:
        lines += ["", "#### 소재 — 보조 기획자가 이 소재·편수로만 기획한 뒤 작가에게",
                  _picks_lines({c.sel: n for c, n in cats}, "커스텀 글쓰기에서 고른 소재")]
    if topics:
        lines += ["", "#### 고정 주제 — 기획 없이 작가에게 바로 (주제마다 편수만큼)"]
        for i, (t, n) in enumerate(topics, start=1):
            lines += ["", f"##### {i}. {t.name}", topic_text(t, today, n)]
    return "\n".join(lines)


def groups():
    """사이트별 묶음 [{name, cats, topics}]: 글 분류의 사이트(대분류) 순서대로 그 소재와 그 사이트의 고정 주제,
    그 뒤로 글 분류에 없는 사이트(예: memorily)의 고정 주제, 마지막에 사이트를 안 정한 고정 주제(name 이 빈 값)."""
    from apps.blog_types.models import Section
    out, by_name = [], {}
    for s in Section.objects.prefetch_related("categories"):
        by_name[s.name] = {"name": s.name, "cats": list(s.categories.all()), "topics": []}
        out.append(by_name[s.name])
    for t in FixedTopic.objects.all():
        key = t.site.strip()
        if key not in by_name:
            by_name[key] = {"name": key, "cats": [], "topics": []}
        by_name[key]["topics"].append(t)
    rest = [g for name, g in by_name.items() if g not in out]
    return out + sorted(rest, key=lambda g: not g["name"])


def _picked(data):
    """폼의 c<번호>=편수 · f<번호>=편수 → ([(Category, n)], [(FixedTopic, n)]). 0·빈칸은 뺀다."""
    from apps.blog_types.models import Category
    want = {}
    for name, raw in data.items():
        if re.fullmatch(r"[cf]\d+", name) and str(raw).strip().isdigit() and int(raw) > 0:
            want[name] = min(int(raw), MAX_EACH)
    cats = Category.objects.filter(pk__in=[k[1:] for k in want if k[0] == "c"]).select_related("section")
    tops = FixedTopic.objects.filter(pk__in=[k[1:] for k in want if k[0] == "f"])
    return [(c, want[f"c{c.pk}"]) for c in cats], [(t, want[f"f{t.pk}"]) for t in tops]


@require_POST
def run(request):
    """고른 소재·고정 주제의 실행 안내문 (JSON). 화면이 받아 복사하고 PC 터미널 claude 를 연다."""
    from .views import launcher, report_url
    writing = Routine.objects.filter(key=WRITING_KEY).first()
    if writing is None:
        return JsonResponse({"error": "글쓰기 루틴이 없습니다."}, status=400)
    cats, topics = _picked(request.POST)
    if not cats and not topics:
        return JsonResponse({"error": "쓸 줄을 체크하세요."}, status=400)
    day = timezone.localdate()
    prompt = launcher(writing, day, report=report_url(request, writing, day), extra=run_text(cats, topics, day), tree=bool(topics))
    names = [c.name for c, _ in cats] + [t.name for t, _ in topics]
    return JsonResponse({"prompt": prompt, "key": writing.key, "day": day.isoformat(),
                         "name": names[0] if len(names) == 1 else f"커스텀 글쓰기 {len(names)}줄",
                         "count": sum(n for _, n in cats) + sum(n for _, n in topics)})


def _back(request, fallback="routines:topics"):
    nxt = request.POST.get("next", "")
    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else fallback)


def page(request):
    request.nav_key = "routine_topics"
    return render(request, "routines/topics.html", {
        "page_title": "커스텀 글쓰기", "groups": groups(), "today": timezone.localdate(), "site_names": sites.names(),
        "writing": Routine.objects.filter(key=WRITING_KEY).first(),
    })


@require_POST
def add(request):
    name = " ".join(request.POST.get("name", "").split())[:60]
    if not name:
        messages.warning(request, "주제 이름을 적으세요.")
        return _back(request)
    order = (FixedTopic.all_objects.aggregate(m=Max("order"))["m"] or 0) + 1
    FixedTopic.objects.create(name=name, order=order, site=request.POST.get("site", "").strip()[:60])
    messages.success(request, f"고정 주제 '{name}'을(를) 추가했습니다. 지침은 연필을 눌러 적으세요.")
    return _back(request)


@require_POST
def save(request, pk):
    topic = get_object_or_404(FixedTopic, pk=pk)
    name = " ".join(request.POST.get("name", "").split())[:60]
    if name:
        topic.name = name
    topic.site = request.POST.get("site", "").strip()[:60]
    topic.note = request.POST.get("note", "").strip()
    topic.save()
    messages.success(request, f"'{topic.name}'을(를) 저장했습니다.")
    return _back(request)


@require_POST
def delete(request, pk):
    topic = get_object_or_404(FixedTopic, pk=pk)
    topic.delete()  # 휴지통으로
    messages.success(request, f"'{topic.name}'을(를) 휴지통으로 옮겼습니다.")
    return _back(request)
