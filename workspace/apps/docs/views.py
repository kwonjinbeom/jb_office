"""시장조사 폴더의 Markdown 문서를 읽기 전용으로 보여 준다."""
from __future__ import annotations

from pathlib import Path

import markdown
from django.conf import settings
from django.http import Http404
from django.shortcuts import render

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "toc"]


def _doc_dirs() -> list[Path]:
    return [Path(d) for d in settings.DOCS_DIRS if Path(d).is_dir()]


def _list_docs() -> list[dict]:
    """[{slug, name, group, path, mtime}] - 폴더별로 .md 파일을 모은다."""
    docs: list[dict] = []
    root = Path(settings.REPO_ROOT)
    for d in _doc_dirs():
        for f in sorted(d.glob("*.md")):
            rel = f.relative_to(root).as_posix()
            docs.append(
                {
                    "slug": rel,
                    "name": f.stem,
                    "group": d.name if d != root else "루트",
                    "path": f,
                    "mtime": f.stat().st_mtime,
                }
            )
    return docs


def _resolve(slug: str) -> Path:
    root = Path(settings.REPO_ROOT).resolve()
    candidate = (root / slug).resolve()
    # 저장소 밖이나 허용 폴더 밖 접근 차단
    if candidate.suffix != ".md" or not candidate.is_file():
        raise Http404
    if candidate.parent not in [d.resolve() for d in _doc_dirs()]:
        raise Http404
    return candidate


def doc_list(request):
    docs = _list_docs()
    groups: dict[str, list[dict]] = {}
    for d in docs:
        groups.setdefault(d["group"], []).append(d)
    return render(request, "docs/list.html", {"page_title": "문서", "groups": groups, "total": len(docs)})


def doc_detail(request, slug):
    path = _resolve(slug)
    text = path.read_text(encoding="utf-8")
    md = markdown.Markdown(extensions=MD_EXTENSIONS)
    html = md.convert(text)
    return render(
        request,
        "docs/detail.html",
        {"page_title": path.stem, "slug": slug, "html": html, "toc": md.toc, "group": path.parent.name},
    )
