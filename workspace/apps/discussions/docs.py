"""논의 글: 저장소의 `논의/**/*.md` 를 '논의 현황'·'진행현황'에 올린다.

Claude·Codex 가 논의를 정리해 md 로 쓰고 push 하면, 서버가 화면을 열 때 이 폴더를 읽어
목록의 한 줄(제목)과 들어가서 보는 글(본문)로 보여 준다. 에이전트는 서버 DB 를 직접 쓰지 않기 때문이다.

글 형식 (맨 위 앞머리 + 본문):

    ---
    제목: 일일 아이디어 운영 방식            ← 목록에 보이는 한 줄. 짧게
    대구분: 일일 아이디어                    ← 일일 아이디어 / 내 아이디어 / 블로그·카페 / 영상 콘텐츠
    중구분:                                 ← (선택) 같은 대구분 안의 상위 주제 이름. 없으면 새로 만든다
    상태: 논의 중                           ← 미논의 / 논의 중 / 결정 / 진행 / 보류 / 완료
    핵심: 한 문장 (140자 안)
    다음 행동: 할 일 하나 (80자 안)
    대화 상대: Claude                       ← 미정 / Codex / Claude / 둘 다
    대화량: 여러 번                         ← 아직 / 조금 / 여러 번 / 많이
    등록: 2026-10-14                        ← (선택) 처음 논의한 날
    날짜: 2026-10-14 16:30                  ← 마지막으로 정리한 때. 목록이 이 날짜 순으로 놓인다
    ---
    # 본문 (Markdown: 표, 이미지, 코드, 그리고 <svg> 같은 HTML 도 그대로)

규칙
- 파일 하나 = 논의 하나. 파일 경로가 이름표라 옮기면 새 논의가 된다.
- 글이 바뀌면(내용 해시가 달라지면) 앞머리 값이 화면에서 고친 상태·핵심·다음 행동을 덮는다.
  글을 고치지 않는 동안은 화면에서 고친 값이 그대로 남는다.
- 이미지는 글 옆에 두고 상대 경로로 쓴다: ![흐름](그림/flow.svg) → discussions:asset 으로 내보낸다.
- README.md 와 이름이 _ 로 시작하는 파일은 논의로 올리지 않는다.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, time
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.docs.views import _render

from .models import Discussion, DiscussionHistory

log = logging.getLogger(__name__)

IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml"}
SNAPSHOT_FIELDS = ["summary", "next_action", "status", "amount", "partner"]


def _choices(pairs, *aliases) -> dict[str, str]:
    """화면 이름(라벨) → 저장 값. 값 자체와 별칭도 받는다."""
    table = {}
    for value, label in pairs:
        table[label] = value
        table[value] = value
    for alias, value in aliases:
        table[alias] = value
    return table


AREAS = _choices(Discussion.AREA_CHOICES, ("블로그/카페", "blog"), ("블로그 카페", "blog"), ("일일아이디어", "daily_ideas"), ("내아이디어", "ideas"), ("영상", "video"))
STATUSES = _choices(Discussion.Status.choices, ("논의중", "talk"))
PARTNERS = _choices(Discussion.Partner.choices, ("claude", "claude"), ("codex", "codex"))
AMOUNTS = _choices(Discussion.Amount.choices, ("여러번", "several"))


def root() -> Path:
    return Path(settings.DISCUSSIONS_DIR)


def parse(text: str) -> tuple[dict[str, str], str]:
    """앞머리(--- 사이의 '이름: 값' 줄)와 본문을 나눈다."""
    text = text.lstrip("﻿")
    meta: dict[str, str] = {}
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                return meta, "\n".join(lines[i + 1:]).lstrip("\n")
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
    return {}, text


def _when(value: str, default_time: time) -> datetime | None:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if fmt == "%Y-%m-%d":
            parsed = datetime.combine(parsed.date(), default_time)
        return timezone.make_aware(parsed)
    return None


def _files():
    base = root()
    if not base.is_dir():
        return []
    return [p for p in sorted(base.rglob("*.md")) if p.name.lower() != "readme.md" and not p.name.startswith("_")]


def sync() -> int:
    """논의 폴더의 글을 DB 에 맞춘다. 바뀐 글만 다시 읽는다. 바꾼 개수를 돌려준다."""
    changed = 0
    repo = Path(settings.REPO_ROOT)
    from apps.core.trash import hidden_keys
    hidden = hidden_keys("discussion")
    for path in _files():
        rel = path.relative_to(repo).as_posix()
        raw = path.read_bytes()
        digest = hashlib.sha1(raw).hexdigest()
        if rel in hidden:
            continue
        item = Discussion.all_objects.filter(doc=rel).first()
        if item and item.deleted_at:
            continue
        if item and item.doc_hash == digest:
            continue
        meta, _ = parse(raw.decode("utf-8", errors="replace"))
        area = AREAS.get(meta.get("대구분", ""))
        name = meta.get("제목", "").strip() or path.stem
        if not area:
            log.warning("논의 글의 대구분을 알 수 없어 건너뜀: %s (%r)", rel, meta.get("대구분"))
            continue
        try:
            _apply(item, rel, digest, area, name, meta)
            changed += 1
        except Exception:  # 글 하나가 잘못돼도 화면은 떠야 한다
            log.exception("논의 글을 올리지 못함: %s", rel)
    return changed


@transaction.atomic
def _apply(item, rel, digest, area, name, meta):
    parent = None
    group = meta.get("중구분", "").strip()
    if group:
        parent = Discussion.objects.filter(area=area, name=group, parent__isnull=True).first()
        if parent is None:
            parent = Discussion.objects.create(area=area, name=group[:80])
    creating = item is None
    if creating:
        item = Discussion(doc=rel)
    before = None if creating else {f: getattr(item, f) for f in SNAPSHOT_FIELDS}
    item.area, item.parent, item.name = area, parent, name[:80]
    item.summary = meta.get("핵심", item.summary or "")[:140]
    item.next_action = meta.get("다음 행동", item.next_action or "")[:80]
    item.status = STATUSES.get(meta.get("상태", ""), item.status if not creating else Discussion.Status.TALK)
    item.partner = PARTNERS.get(meta.get("대화 상대", ""), item.partner)
    item.amount = AMOUNTS.get(meta.get("대화량", ""), item.amount)
    item.doc_hash = digest
    item.save()

    # 글에 적힌 날짜를 목록의 날짜로 쓴다 (auto_now 를 피해 update 로).
    stamps = {}
    updated = _when(meta.get("날짜", ""), time(12, 0))
    if updated:
        stamps["updated_at"] = updated
    created = _when(meta.get("등록", ""), time(9, 0)) or (updated if creating else None)
    if created:
        stamps["created_at"] = created
    if stamps:
        Discussion.objects.filter(pk=item.pk).update(**stamps)

    after = {f: getattr(item, f) for f in SNAPSHOT_FIELDS}
    if before != after:
        previous = item.history.first()
        record = DiscussionHistory.objects.create(discussion=item, **after)
        # 이력 시각은 글의 날짜로. 단 화면에서 그 뒤에 고친 이력이 있으면 지금 시각 그대로 둬서,
        # 맨 위 이력이 늘 지금 값과 같게 한다.
        if updated and (previous is None or updated > previous.created_at):
            DiscussionHistory.objects.filter(pk=record.pk).update(created_at=updated)


def post(item: Discussion) -> dict | None:
    """상세 화면에 보일 글. 글이 없으면 None, 파일이 사라졌으면 missing."""
    if not item.doc:
        return None
    path = (Path(settings.REPO_ROOT) / item.doc).resolve()
    if not path.is_file() or root().resolve() not in path.parents:
        return {"missing": True, "path": item.doc}
    _, body = parse(path.read_text(encoding="utf-8", errors="replace"))
    html, toc = _render(body)
    folder = path.parent.relative_to(root().resolve()).as_posix()
    return {"html": _rewrite_assets(html, folder), "toc": toc, "path": item.doc, "has_toc": "<li" in toc}


_SRC = re.compile(r'(\s(?:src|href))="(?!https?:|/|#|data:|mailto:)([^"]+)"')


def _rewrite_assets(html: str, folder: str) -> str:
    """글 옆의 그림을 상대 경로로 쓴 것을 내려받을 수 있는 주소로 바꾼다."""
    base = reverse("discussions:asset", args=["x"])[:-1]

    def repl(m):
        rel = f"{folder}/{m.group(2)}" if folder not in ("", ".") else m.group(2)
        return f'{m.group(1)}="{base}{quote(rel)}"'

    return _SRC.sub(repl, html)


def asset_path(rel: str) -> Path | None:
    """논의 폴더 안의 그림 파일만 내준다."""
    base = root().resolve()
    path = (base / rel).resolve()
    if base not in path.parents or not path.is_file() or path.suffix.lower() not in IMAGE_TYPES:
        return None
    return path
