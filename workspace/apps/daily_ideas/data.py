"""저장소에 날짜별로 쌓이는 일일 아이디어 JSON을 읽는다.

파일: 시장조사/일일아이디어/<YYYY-MM-DD>.json  (날짜마다 하나)
  { "date": "2026-10-14", "title": "...", "summary": "...", "method": "...", "source_doc": "...", "items": [ ... ] }
항목의 필수 값은 REQUIRED_FIELDS. 선택 값:
  tags  ["CSV", "엑셀"]
  plan  구현 계획. 화면에서 항목을 누르면 펼쳐진다. 없으면 만들 것·첫 검증·알릴 곳·돈 받는 방식으로 대신한다.
        ["1주차: ...", "2주차: ..."]  또는  [{"title": "1주차", "detail": "..."}, ...]
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.conf import settings


CATEGORY_LABELS = {
    "tool": "도구",
    "service": "서비스",
    "search": "검색·데이터",
    "content": "원본 콘텐츠",
    "digital": "디지털 상품",
}

REQUIRED_FIELDS = {
    "id",
    "title",
    "category",
    "audience",
    "problem",
    "min_product",
    "money_flow",
    "channel",
    "evidence",
    "risk",
    "first_test",
    "decision",
    "sources",
}


# plan 이 없는 항목은 이 네 가지를 순서대로 구현 계획으로 보여 준다.
PLAN_FALLBACK = (
    ("만들 것", "min_product"),
    ("첫 검증", "first_test"),
    ("알릴 곳", "channel"),
    ("돈 받는 방식", "money_flow"),
)


def _plan_steps(raw: dict) -> list[dict]:
    steps: list[dict] = []
    plan = raw.get("plan")
    if isinstance(plan, list):
        for step in plan:
            if isinstance(step, dict):
                title, detail = str(step.get("title", "")).strip(), str(step.get("detail", "")).strip()
            else:
                title, detail = "", str(step).strip()
            if title or detail:
                steps.append({"title": title, "detail": detail})
    if steps:
        return steps
    return [
        {"title": label, "detail": str(raw[key]).strip()}
        for label, key in PLAN_FALLBACK
        if str(raw.get(key, "")).strip()
    ]


def _load_file(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        batch = json.load(fh)

    batch_date = str(batch.get("date", ""))
    date.fromisoformat(batch_date)
    items = batch.get("items")
    if not isinstance(items, list):
        raise ValueError(f"{path}: items must be a list")

    seen: set[str] = set()
    normalized: list[dict] = []
    for raw in items:
        missing = REQUIRED_FIELDS.difference(raw)
        if missing:
            raise ValueError(f"{path}: missing {sorted(missing)}")
        item_id = str(raw["id"])
        if item_id in seen:
            raise ValueError(f"{path}: duplicate id {item_id}")
        if raw["category"] not in CATEGORY_LABELS:
            raise ValueError(f"{path}: unknown category {raw['category']}")
        if not isinstance(raw["sources"], list):
            raise ValueError(f"{path}: sources must be a list")
        seen.add(item_id)
        item = dict(raw)
        item["category_label"] = CATEGORY_LABELS[item["category"]]
        item["date"] = batch_date
        item["source_doc"] = batch.get("source_doc", f"시장조사/일일아이디어_{batch_date}.md")
        item["daily_tag"] = f"daily:{item_id}"
        item["plan_steps"] = _plan_steps(raw)
        normalized.append(item)

    result = dict(batch)
    result["items"] = normalized
    result["date"] = batch_date
    result["source_doc"] = batch.get("source_doc", f"시장조사/일일아이디어_{batch_date}.md")
    return result


def load_batches() -> list[dict]:
    data_dir = Path(settings.DAILY_IDEAS_DIR)
    if not data_dir.exists():
        return []
    return [_load_file(path) for path in sorted(data_dir.glob("*.json"), reverse=True)]


def find_item(item_id: str) -> dict | None:
    for batch in load_batches():
        for item in batch["items"]:
            if item["id"] == item_id:
                return item
    return None
