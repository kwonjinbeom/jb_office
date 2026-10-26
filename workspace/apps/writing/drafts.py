"""저장소의 원고 폴더(콘텐츠/블로그_카페/포스팅자동화/원고/T??_*/원고.md)를 읽어 임시글으로 가져온다.

Claude 가 원고.md 를 써서 main 에 올리면 서버에도 같은 파일이 있다 (웹훅이 git pull).
'원고 가져오기' 화면에서 고르면 본문(마크다운)·제목·태그·소개가 그대로 들어간다.
T88 부터(일일루틴 글쓰기, 2026-10-22 임시글 정리 뒤)는 글 관리를 열 때 저절로 들어간다 (views.auto_import_drafts).

원고.md 형식 (원고/README.md):
  위쪽 제작 정보 → <!-- 본문 시작 --> → # 제목 → 본문 → <!-- 본문 끝 --> → 태그: … → 소개: …
  제작 정보의 `사이트: …` · `분류: 대 > 중 > 소` 줄(일일루틴 글쓰기)은 가져올 때 사이트·글 분류로 쓴다.
  제작 정보 표의 `| 넣을 카테고리 | 사이트 › 카테고리 |` 는 발행예정글로 옮길 때 기본으로 넣는 곳 (blog_types.sites.place_defaults).
  `고정주제: …` · `커스텀: …` 줄이 있으면 커스텀 글 (일일루틴 하루 분량이 아닌 글, 글 관리의 '커스텀'으로 따로 본다).
"""
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
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
    custom: bool = False
    place: str = ""  # 넣을 카테고리 '사이트 › 카테고리' (처음 겨냥한 곳)
    topic: str = ""  # 고정 주제 이름 (`고정주제: AI 소식` 줄). 일일루틴 글쓰기 결과에서 'memorily > AI 소식' 처럼 보인다
    old_titles: tuple = ()  # `옛 제목: …` 줄 (2026-10-26: 이미 있는 글을 허브로 바꾸며 제목을 고칠 때, 그 글을 알아보게)
    change: str = ""  # `고친 내용: …` 줄 — 변환글 보기 맨 위 '수정됨' 한 줄에 붙는다 (2026-10-26 사용자)

    @property
    def code(self) -> str:
        return self.key.split("_", 1)[0]


def parse(text: str, key: str = "", modified: float = 0.0) -> Draft | None:
    """원고.md 한 편. 본문 표시가 없거나 제목(본문 첫 줄 # … 또는 맨 위 # [원고] T번호 · …)이 없으면 None."""
    if START not in text:
        return None
    body = text.split(START, 1)[1].split(END, 1)[0].strip()
    m = re.match(r"#\s+(.+)\n*", body)
    if m:
        title = m.group(1).strip()
        body = body[m.end():]
    else:  # 본문에 제목 줄이 없으면 맨 위 '# [원고] T61 · 제목' 에서 (2026-10-20: T61·T62 가 이래서 안 들어왔다)
        head_title = re.match(r"#\s*\[원고\]\s*\S+\s*·\s*(.+)", text.lstrip())
        if not head_title:
            return None
        title = head_title.group(1).strip()
    body = re.sub(r"^> 제목 대안:.*\n+", "", body, flags=re.M).strip()  # 제목 후보 줄은 제작 정보
    tail = text.split(END, 1)[1] if END in text else ""
    head = text.split(START, 1)[0]
    site = re.search(r"^[-*\s]*`?사이트:\s*([^`\n]+)`?\s*$", head, re.M)
    classification = re.search(r"^[-*\s]*`?분류:\s*([^`\n]+)`?\s*$", head, re.M)
    tags = re.search(r"^태그:\s*(.+)$", tail, re.M)
    summary = re.search(r"^소개:\s*(.+)$", tail, re.M)
    custom = re.search(r"^[-*\s]*`?(?:고정주제|커스텀):", head, re.M)
    topic = re.search(r"^[-*\s]*`?고정주제:\s*([^`\n]+)`?\s*$", head, re.M)
    place = re.search(r"^\|\s*넣을 카테고리\s*\|\s*([^|\n]+?)\s*\|", head, re.M)
    change = re.search(r"^[-*\s]*`?고친 내용:\s*([^`\n]+)`?\s*$", head, re.M)
    old_titles = tuple(t.strip()[:200] for t in re.findall(r"^[-*\s]*`?옛 제목:\s*([^`\n]+)`?\s*$", head, re.M) if t.strip())
    return Draft(
        key=key,
        title=title[:200],
        body=body,
        tags=tags.group(1).strip()[:300] if tags else "",
        summary=summary.group(1).strip()[:300] if summary else "",
        modified=modified,
        site=site.group(1).strip()[:60] if site else "",
        classification=classification.group(1).strip()[:200] if classification else "",
        custom=bool(custom),
        topic=topic.group(1).strip()[:60] if topic else "",
        old_titles=old_titles,
        change=change.group(1).strip()[:120] if change else "",
        place=re.sub(r"\s*\([^)]*\)\s*$", "", place.group(1)).strip()[:120] if place else "",  # '(신설 제안)' 같은 꼬리는 뺀다
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


def written_at(draft: "Draft", root: Path | None = None) -> datetime:
    """원고를 쓴 때 = 원고.md 가 git 에 처음 올라온 시각 (없으면 파일 수정 시각).

    가져온 글의 '만든 날'로 쓴다 — 가져온 때로 찍으면 밤에 쓴 원고가 다음 날 글이 된다 (2026-10-16 사용자).
    """
    f = (root or drafts_dir()) / draft.key / "원고.md"
    try:
        out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%cI", "-1", "--", f.name],
                             cwd=f.parent, capture_output=True, text=True, timeout=10).stdout.strip()
        if out:
            return datetime.fromisoformat(out)
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return datetime.fromtimestamp(draft.modified, tz=timezone.utc)
