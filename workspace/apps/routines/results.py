"""일일루틴 '글쓰기 결과': 그날 기획표(주제기획/<날짜>.md)의 소재 판정 + 그날 쓴 글을 분류(사이트 > 소재)마다 한 줄로.

2026-10-23 사용자: 전체 실행에서 18편 중 5편만 나와 이유를 물었다 → 왜 몇 편만 썼는지 화면에서 바로 보게.
판정: 씀(그날 그 분류 글이 있음) · 예정(코스피, 15:30 장 마감 전) · 못 씀(기획은 '있음'인데 글이 없음) · 없음(소재 없음).
글은 T번호가 아니라 제목으로 보인다 (사용자는 T번호로 어떤 글인지 모른다).
"""
import re
from datetime import date

from django.urls import reverse

STATES = {  # 키 → (말, 뱃지 색) · 이 순서로 줄을 세운다
    "done": ("씀", "green"),
    "planned": ("예정", "amber"),
    "missed": ("못 씀", "red"),
    "none": ("없음", "gray"),
}
ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(있음|없음|예정)\s*\|\s*(.*?)\s*\|?\s*$")


def plan_dir():
    from apps.writing.drafts import drafts_dir
    return drafts_dir().parent / "주제기획"


def _label(text):
    return re.sub(r"\s*>\s*", " > ", text.strip())


def _bare(label):
    return re.sub(r"\s+", "", label)


def verdicts(day: date):
    """그날 기획표의 '소재 판정' → {'사이트 > 소재': (있음|없음|예정, 근거)}. 그날 두 번째 기획(_2)이 뒤에서 덮는다."""
    out = {}
    folder = plan_dir()
    if not folder.is_dir():
        return out
    for f in sorted(folder.glob(f"{day.isoformat()}*.md")):
        if not re.fullmatch(rf"{day.isoformat()}(_\d+)?\.md", f.name):
            continue
        section = False
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                section = line.strip() == "## 소재 판정"
                continue
            m = ROW.match(line) if section else None
            if m:
                out[_label(m[1])] = (m[2], m[3])
    return out


def _posts(day):
    """그날 만든 글 (티스토리·네이버 표) → {'사이트 > 소재': [(제목, 주소)]}. 분류가 없으면 '사이트 > 고정 주제'
    (원고의 `고정주제:` 줄, 예: memorily > AI 소식), 그것도 없으면 사이트 이름."""
    from apps.naver_writing.models import Post as NaverPost
    from apps.writing import drafts
    from apps.writing.models import Post
    from .models import FixedTopic
    topics = {d.title: d.topic for d in drafts.list_drafts() if d.topic}
    topic_cats = {t.name: f"{t.category.section.name} > {t.category.name}"  # 소재를 정한 고정 주제는 그 소재로 (AI 소식 → memorily > AI)
                  for t in FixedTopic.objects.exclude(category=None).select_related("category__section")}
    out = {}
    for model, ns in ((Post, "writing"), (NaverPost, "naver_writing")):
        for p in model.objects.filter(created_at__date=day).select_related("bt_category__section").order_by("created_at", "pk"):
            cat = p.bt_category
            if cat:
                label = f"{cat.section.name} > {cat.name}"
            elif p.title in topics:
                label = topic_cats.get(topics[p.title]) or f"{p.target or '사이트 미정'} > {topics[p.title]}"
            else:
                label = p.target or "분류 없음"
            out.setdefault(label, []).append((p.title, reverse(f"{ns}:detail", args=[p.pk])))
    return out


def _daily_topics():
    """전체 실행에 매일 붙는 고정 주제 (FixedTopic.daily) → {'사이트 > 주제' 또는 '사이트 > 소재': 주제 이름}"""
    from .models import FixedTopic
    out = {}
    for t in FixedTopic.objects.filter(daily=True).select_related("category__section"):
        label = f"{t.category.section.name} > {t.category.name}" if t.category_id else f"{t.site or '사이트 미정'} > {t.name}"
        out[label] = t.name
    return out


def writing_results(day: date):
    """[{label, sel, state, word, color, posts, reason}] — 글 분류 순서로, 씀 → 예정 → 못 씀 → 없음.
    매일 쓰는 고정 주제(AI 소식)는 기획표 판정이 없어도 '있음'으로 본다 — 원고가 없으면 '못 씀'."""
    from apps.blog_types.models import Category
    plans, posts = verdicts(day), _posts(day)
    if plans:
        for label, name in _daily_topics().items():
            plans.setdefault(label, ("있음", f"매일 쓰는 고정 주제 ({name})"))
    if not plans and not posts:
        return []
    cats = {_bare(f"{c.section.name} > {c.name}"): (f"{c.section.name} > {c.name}", c.sel)
            for c in Category.objects.select_related("section").order_by("section__order", "section__pk", "order", "pk")}
    names = {_bare(k): k for k in list(plans) + list(posts)}
    plans = {_bare(k): v for k, v in plans.items()}  # 띄어쓰기만 다른 이름('해외여행' ↔ '해외 여행')은 같은 분류
    posts = {_bare(k): v for k, v in posts.items()}
    keys = [k for k in cats if k in plans or k in posts]
    keys += [k for k in list(plans) + list(posts) if k not in keys and k not in cats]
    rows = []
    for key in keys:
        label, sel = cats.get(key, (names.get(key, key), ""))
        verdict, reason = plans.get(key, ("", ""))
        written = posts.get(key, [])
        if written:
            state = "done"
            if verdict != "있음":
                reason = "커스텀 글쓰기" if not verdict else "기획 밖에서 씀 (대체·커스텀)"
        elif verdict == "예정":
            state = "planned"
        elif verdict == "있음":
            daily = reason.startswith("매일 쓰는")
            state = "missed"
            reason = (f"{reason} — 원고가 없음, 글감 없음이면 실행 이력에" if daily
                      else "기획은 '있음'인데 원고가 없음 — 실행 이력의 막힘을 보세요")
        else:
            state = "none"
        word, color = STATES[state]
        rows.append({"label": label, "sel": sel, "state": state, "word": word, "color": color,
                     "posts": written, "reason": reason})
    order = list(STATES)
    return sorted(rows, key=lambda r: order.index(r["state"]))


def counts(rows):
    """[(말, 색, 수)] — 머리에 '씀 5 · 예정 1 · 없음 10'."""
    return [(word, color, n) for key, (word, color) in STATES.items() if (n := sum(1 for r in rows if r["state"] == key))]
