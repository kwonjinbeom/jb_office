"""저장소의 원고 폴더(콘텐츠/블로그_카페/포스팅자동화/원고/T??_*/원고.md)를 읽어 임시 템플릿으로 가져온다.

Claude 가 원고.md 를 써서 main 에 올리면 서버에도 같은 파일이 있다 (웹훅이 git pull).
'원고 가져오기' 화면에서 고르면 본문(마크다운)·제목·태그·소개가 그대로 들어간다.

원고.md 형식 (원고/README.md):
  위쪽 제작 정보 → <!-- 본문 시작 --> → # 제목 → 본문 → <!-- 본문 끝 --> → 태그: … → 소개: …
  제작 정보의 `사이트: …` · `분류: 대 > 중 > 소` 줄(일일루틴 글쓰기)은 가져올 때 사이트·글 분류로 쓴다.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

START, END = "<!-- 본문 시작 -->", "<!-- 본문 끝 -->"


def drafts_dir() -> Path:
    return Path(getattr(settings, "WRITING_DRAFTS_DIR",
                        settings.REPO_ROOT / "콘텐츠" / "블로그_카페" / "포스팅자동화" / "원고"))


@dataclass
class Draft:
    key: str  # 폴더 이름 (T01_독감무료접종)
    title: str
    body: str
    tags: str
    summary: str
    modified: float
    site: str = ""
    classification: str = ""

    @property
    def code(self) -> str:
        return self.key.split("_", 1)[0]


def parse(text: str, key: str = "", modified: float = 0.0) -> Draft | None:
    """원고.md 한 편. 본문 표시가 없거나 제목(# …)이 없으면 None."""
    if START not in text:
        return None
    body = text.split(START, 1)[1].split(END, 1)[0].strip()
    m = re.match(r"#\s+(.+)\n*", body)
    if not m:
        return None
    title = m.group(1).strip()
    body = body[m.end():]
    body = re.sub(r"^> 제목 대안:.*\n+", "", body, flags=re.M).strip()  # 제목 후보 줄은 제작 정보
    tail = text.split(END, 1)[1] if END in text else ""
    head = text.split(START, 1)[0]
    site = re.search(r"^[-*\s]*`?사이트:\s*([^`\n]+)`?\s*$", head, re.M)
    classification = re.search(r"^[-*\s]*`?분류:\s*([^`\n]+)`?\s*$", head, re.M)
    tags = re.search(r"^태그:\s*(.+)$", tail, re.M)
    summary = re.search(r"^소개:\s*(.+)$", tail, re.M)
    return Draft(
        key=key,
        title=title[:200],
        body=body,
        tags=tags.group(1).strip()[:300] if tags else "",
        summary=summary.group(1).strip()[:300] if summary else "",
        modified=modified,
        site=site.group(1).strip()[:60] if site else "",
        classification=classification.group(1).strip()[:200] if classification else "",
    )


def list_drafts(root: Path | None = None) -> list[Draft]:
    root = root or drafts_dir()
    if not root.is_dir():
        return []
    out = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        f = folder / "원고.md"
        if not f.is_file():
            continue
        d = parse(f.read_text(encoding="utf-8"), folder.name, f.stat().st_mtime)
        if d:
            out.append(d)
    return out
