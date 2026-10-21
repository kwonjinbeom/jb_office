"""블로그·카페 › memorily 티스토리 › 애니 총정리 (2026-10-21 사용자).

나루토처럼 애니↔만화 환산기 글을 작품마다 더 쓰기 위한 md 를 보여 준다 (읽기 전용, DB 없음).
폴더 settings.ANIME_DIR: 00_작업순서.md (모든 작품 공통) + 작품마다 md 하나. 작품 md 의 `상태:` 줄을 목록에 보인다.
md 는 Claude 가 저장소에서 고치고 main 에 올린다 — 서버는 git pull 로 같은 파일을 읽는다.
"""
import re
from pathlib import Path

import markdown
from django.conf import settings
from django.shortcuts import render

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists"]


def _docs():
    root = Path(settings.ANIME_DIR)
    if not root.is_dir():
        return []
    out = []
    for f in sorted(root.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        title = re.search(r"^#\s+(.+)$", text, re.M)
        status = re.search(r"^상태:\s*(.+)$", text, re.M)
        out.append({"key": f.stem, "title": title.group(1).strip() if title else f.stem,
                    "status": status.group(1).strip() if status else "", "text": text,
                    "guide": f.stem.startswith("00")})
    return out


def index(request):
    docs = _docs()
    current = next((d for d in docs if d["key"] == request.GET.get("d")), docs[0] if docs else None)
    html = markdown.markdown(current["text"], extensions=MD_EXTENSIONS) if current else ""
    return render(request, "anime/index.html", {
        "page_title": "애니 총정리", "docs": docs, "current": current, "html": html,
        "works": sum(1 for d in docs if not d["guide"]),
    })
