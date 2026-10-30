"""주제 겹침 검사: 기획표의 '- 대상:' 낱말이 지난 원고 제목·폴더 이름에 있는지 기계로 찾는다.

왜 (2026-10-31 사용자): T210 지스타 2026 이 T114(10-23, 8일 전)와 같은 행사였다. 기획자는 장부(중분류마다 최근 5편)만 보고
'장부에 없음', 작가는 '원고 폴더에 없음'이라 적었다 — 프롬프트의 Grep 지시만으로는 막히지 않았다.
그래서 기획표가 오면 메인이 `manage.py check_overlap <기획표>` 를 돌리고, 겹침이 있으면 그 슬롯을 다음 후보로 바꾼다.
'반복 점검' 줄에 그 T번호를 적었으면(큰 변화로 '바뀐 것' 각도) 예외로 보고, '허브' 줄의 폴더는 같은 글을 고치는 것이라 뺀다.
날마다 쓰는 시황 노트·고정 코너는 `- 대상: 없음 (시황 노트)` 로 건너뛴다.
"""
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from django.utils import timezone

from apps.writing import drafts

WINDOW_DAYS = 21  # writing_topics.md 5단계: 같은 대상은 21일 안에 다시 쓰지 않는다
OLD_SHOWN = 3  # 21일 넘은 겹침은 참고로 몇 편까지
SLOT = re.compile(r"^###\s*(T\d+)\s*·\s*(.+)$", re.M)


@dataclass
class Hit:
    code: str
    title: str
    day: date
    days: int
    noted: bool = False  # 반복 점검 줄에 그 T번호를 적었다 (바뀐 것 각도)


@dataclass
class Slot:
    code: str
    label: str
    words: list
    note: str = ""
    hub: str = ""
    hits: list = field(default_factory=list)
    daily: bool = False  # '대상: 없음' — 날마다 쓰는 소재라 검사하지 않는다

    @property
    def blocked(self):
        """막힌 슬롯: 대상 줄이 없거나, 21일 안 겹침을 반복 점검에 적지 않았다."""
        if self.daily:
            return False
        return not self.words or any(h.days <= WINDOW_DAYS and not h.noted for h in self.hits)


def _line(block: str, name: str) -> str:
    m = re.search(rf"^-\s*{name}[^:\n]*:\s*(.*)$", block, re.M)
    return m.group(1).strip() if m else ""


def split_words(text: str) -> list:
    return [w.strip() for w in re.split(r"[,·/|]", text) if len(_bare(w)) >= 2]


def parse_plan(text: str) -> list:
    """기획표 '### T210 · 사이트 > 소재 · 글 틀' 슬롯마다 대상 낱말 · 반복 점검 · 허브."""
    heads = list(SLOT.finditer(text))
    out = []
    for i, m in enumerate(heads):
        block = text[m.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        block = block.split("\n## ", 1)[0]  # 다음 큰 칸('오늘 배운 것')은 빼고
        target = _line(block, "대상")
        out.append(Slot(m.group(1), m.group(2).strip(), [] if target.startswith("없음") else split_words(target),
                        _line(block, "반복 점검"), _line(block, "허브"), daily=target.startswith("없음")))
    return out


def _bare(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def find(words, day: date, skip=(), root: Path | None = None) -> list:
    """낱말이 제목·옛 제목·폴더 이름에 든 원고 (최근 것부터). skip: 뺄 T번호·폴더 이름."""
    keys = [_bare(w) for w in words if _bare(w)]
    hits = []
    for d in drafts.list_drafts(root):
        if d.code in skip or d.key in skip:
            continue
        hay = _bare(" ".join((d.key, d.title, *d.old_titles)))
        if not any(k in hay for k in keys):
            continue
        made = timezone.localtime(drafts.written_at(d, root)).date()
        hits.append(Hit(d.code, d.title, made, (day - made).days))
    return sorted(hits, key=lambda h: h.days)


def check_plan(path: Path, root: Path | None = None) -> list:
    m = re.match(r"(\d{4}-\d{2}-\d{2})", path.name)
    day = date.fromisoformat(m.group(1)) if m else date.today()
    slots = parse_plan(path.read_text(encoding="utf-8"))
    codes = {s.code for s in slots}
    for s in slots:
        skip = codes | ({Path(s.hub).name} if s.hub and s.hub not in ("없음", "-") else set())
        s.hits = find(s.words, day, skip, root)
        for h in s.hits:
            h.noted = h.code in re.findall(r"T\d+", s.note)
    return slots


def report(slots) -> list:
    lines = []
    for s in slots:
        if s.daily:
            lines.append(f"{s.code} · {s.label}: 대상 없음 (날마다 쓰는 소재) — 건너뜀")
            continue
        if not s.words:
            lines.append(f"{s.code} · {s.label}: 대상 줄 없음 — 기획표에 '- 대상: 낱말1 · 낱말2' 를 적고 다시 돌린다")
            continue
        head = f"{s.code} · {' · '.join(s.words)}"
        near = [h for h in s.hits if h.days <= WINDOW_DAYS]
        old = [h for h in s.hits if h.days > WINDOW_DAYS][:OLD_SHOWN]
        if not s.hits:
            lines.append(f"{head}: 겹침 없음")
        for h in near:
            mark = "예외(반복 점검에 적음)" if h.noted else f"겹침 — {WINDOW_DAYS}일 안, 다음 후보로 바꾼다"
            lines.append(f"{head}: {mark} · {h.code} ({h.day}, {h.days}일 전) {h.title}")
        for h in old:
            lines.append(f"{head}: 참고 ({h.days}일 전) {h.code} {h.title}")
    return lines
