"""AI 가 고친 글 분류를 DB 에 반영한다: 저장소 일일루틴/분류변경/*.json → 중·소·하위 분류 추가·이름 고치기.

글쓰기 루틴(일일루틴/프롬프트/writing.md)이 트렌드·화제 때문에 분류가 필요하면 파일을 하나 남기고 main 에 올린다.
서버는 git pull 로 파일을 받고, 글 분류·일일루틴 화면을 열 때 sync() 가 아직 반영 안 한 파일만 반영한다 (논의 md 와 같은 방식).
대분류는 고치지 않는다. 지우기도 하지 않는다 (지우는 건 사람이 화면에서).

파일 형식 (일일루틴/분류변경/README.md):
{"date": "2026-10-17", "reason": "왜", "changes": [
  {"op": "add", "parent": "black_lukey", "name": "새 소재", "direction": "", "question": ""},
  {"op": "rename", "path": "눈잎 > 해외 여행", "to": "동남아·해외 여행"}
  (예전 트리처럼 소재 아래 소·하위를 더하는 것도 되지만 2026-10-22 부터 쓰지 않는다)
]}
경로는 ' > ' 로 잇고, 중분류는 기호 없이 이름만 (기호를 붙여도 된다: "B 정책·내 돈").
"""
import json
import re
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Max

from .models import Category, ClassChange, PostType, Section, SubType

FOLDER = ("일일루틴", "분류변경")


def folder() -> Path:
    return Path(settings.REPO_ROOT).joinpath(*FOLDER)


def _match(qs, name, field="name"):
    name = name.strip()
    objs = list(qs)
    for obj in objs:
        if getattr(obj, field) == name:
            return obj
    bare = re.sub(r"\s+", "", name)  # 띄어쓰기만 다르면 같은 것 (2026-10-23: 원고 '해외여행' ↔ 분류 '해외 여행')
    for obj in objs:
        if re.sub(r"\s+", "", getattr(obj, field)) == bare:
            return obj
    return None


def resolve(path):
    """'대 > 중 > 소 > 하위' → 그 노드 (없으면 None)."""
    parts = [p.strip() for p in path.split(">") if p.strip()]
    if not parts:
        return None
    node = _match(Section.objects.all(), parts[0])
    for depth, part in enumerate(parts[1:], start=1):
        if node is None:
            return None
        if depth == 1:
            code = re.match(r"^([A-Z]{1,2})[.\s]\s*(.+)$", part)
            cats = list(node.categories.all())
            node = (_match(cats, code.group(2)) if code else None) or _match(cats, part)
        elif depth == 2:
            node = _match(node.types.all(), part)
        elif depth == 3:
            node = _match(node.subs.all(), part)
        else:
            return None
    return node


def _next_code(section):
    used = set(section.categories.values_list("code", flat=True))
    for i in range(26 * 2):
        code = chr(65 + i) if i < 26 else "A" + chr(65 + i - 26)
        if code not in used:
            return code
    return "Z"


def _apply(change):
    op = change.get("op")
    if op == "add":
        parent, name = resolve(change.get("parent", "")), (change.get("name") or "").strip()[:80]
        if parent is None or not name:
            return f"건너뜀: 추가할 곳 없음 ({change.get('parent')})"
        if isinstance(parent, Section):
            if _match(parent.categories.all(), name):
                return f"이미 있음: {name}"
            Category.objects.create(section=parent, code=_next_code(parent), name=name[:40],
                                    direction=(change.get("direction") or "")[:120], question=(change.get("question") or "")[:160],
                                    order=(parent.categories.aggregate(m=Max("order"))["m"] or 0) + 1)
        elif isinstance(parent, Category):
            if _match(parent.types.all(), name):
                return f"이미 있음: {name}"
            PostType.objects.create(category=parent, name=name[:60], order=(parent.types.aggregate(m=Max("order"))["m"] or 0) + 1)
        elif isinstance(parent, PostType):
            if _match(parent.subs.all(), name):
                return f"이미 있음: {name}"
            SubType.objects.create(post_type=parent, name=name, order=(parent.subs.aggregate(m=Max("order"))["m"] or 0) + 1)
        else:
            return "건너뜀: 하위 아래에는 더 못 만든다"
        return f"추가: {change.get('parent')} > {name}"
    if op == "rename":
        node, to = resolve(change.get("path", "")), (change.get("to") or "").strip()
        if node is None or not to:
            return f"건너뜀: 고칠 곳 없음 ({change.get('path')})"
        if isinstance(node, Section):
            return "건너뜀: 대분류는 고치지 않는다"
        node.name = to[:{Category: 40, PostType: 60}.get(type(node), 80)]
        node.save(update_fields=["name"])
        return f"이름: {change.get('path')} → {to}"
    return f"건너뜀: 모르는 op ({op})"


def sync() -> int:
    """아직 반영 안 한 변경 파일을 이름 순서대로 반영한다. 반영한 파일 수."""
    root = folder()
    if not root.is_dir():
        return 0
    done = set(ClassChange.objects.values_list("name", flat=True))
    count = 0
    for f in sorted(root.glob("*.json")):
        if f.name in done:
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            with transaction.atomic():
                lines = [_apply(c) for c in data.get("changes", [])]
            ok = not any(line.startswith("건너뜀") for line in lines)
            log = "\n".join([data.get("reason", ""), *lines]).strip()
        except (ValueError, AttributeError, TypeError) as e:
            ok, log = False, f"파일을 읽지 못함: {e}"
        ClassChange.objects.create(name=f.name, ok=ok, log=log)
        count += 1
    return count
