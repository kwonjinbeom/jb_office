"""저장소에 날짜별로 쌓이는 일일 아이디어 JSON을 읽는다."""

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
