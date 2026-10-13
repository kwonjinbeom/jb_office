"""시장조사 폴더의 Markdown 문서를 읽기 전용으로 보여 준다.

Markdown 패키지가 있으면 그것을 쓰고, 없으면 내장 간이 변환기로 대신한다.
(서버에 패키지가 아직 설치되지 않은 순간에도 화면이 죽지 않게 하기 위해서다.)
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

try:  # 선택 의존성
    import markdown as _markdown
except ImportError:  # pragma: no cover
    _markdown = None

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "toc"]


def _doc_dirs() -> list[Path]:
    return [Path(d) for d in settings.DOCS_DIRS if Path(d).is_dir()]


def _list_docs() -> list[dict]:
    docs: list[dict] = []
    root = Path(settings.REPO_ROOT)
    for d in _doc_dirs():
        for f in sorted(d.glob("*.md")):
            rel = f.relative_to(root).as_posix()
            docs.append({"slug": rel, "name": f.stem, "group": d.name if d != root else "루트", "path": f})
    return docs


def _resolve(slug: str) -> Path:
    root = Path(settings.REPO_ROOT).resolve()
    candidate = (root / slug).resolve()
    if candidate.suffix != ".md" or not candidate.is_file():
        raise Http404
    if candidate.parent not in [d.resolve() for d in _doc_dirs()]:
        raise Http404
    return candidate


# ---- 내장 간이 변환기 (제목, 문단, 목록, 표, 코드, 굵게, 링크, 인용) ----

_INLINE_RULES = [
    (re.compile(r"`([^`]+)`"), r"<code>\1</code>"),
    (re.compile(r"\*\*([^*]+)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)"), r'<a href="\2" target="_blank" rel="noopener">\1</a>'),
    (re.compile(r"(?<![\"'>])(https?://[^\s<)]+)"), r'<a href="\1" target="_blank" rel="noopener">\1</a>'),
]


def _inline(text: str) -> str:
    out = html.escape(text, quote=False)
    for rx, rep in _INLINE_RULES:
        out = rx.sub(rep, out)
    return out


def _simple_markdown(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    out: list[str] = []
    toc: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("```"):
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(html.escape(lines[i]))
                i += 1
            i += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            anchor = f"h-{len(toc)+1}"
            toc.append(f'<li style="padding-left:{(level-1)*10}px"><a href="#{anchor}">{html.escape(title)}</a></li>')
            out.append(f'<h{level} id="{anchor}">{_inline(title)}</h{level}>')
            i += 1
            continue
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|?\s*:?-{2,}", lines[i + 1].strip()):
            header = [c.strip() for c in stripped.strip("|").split("|")]
            rows = []
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append("<table><thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in header) + "</tr></thead><tbody>")
            for r in rows:
                out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
            out.append("</tbody></table>")
            continue
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(_inline(lines[i].strip()[1:].strip()))
                i += 1
            out.append("<blockquote><p>" + "<br>".join(buf) + "</p></blockquote>")
            continue
        if re.match(r"^(\d+\.|[-*])\s+", stripped):
            ordered = stripped[0].isdigit()
            tag = "ol" if ordered else "ul"
            items = []
            while i < n and re.match(r"^\s*(\d+\.|[-*])\s+", lines[i]):
                items.append(re.sub(r"^\s*(\d+\.|[-*])\s+", "", lines[i]))
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + f"</{tag}>")
            continue
        buf = []
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6}\s|```|\||>|\d+\.\s|[-*]\s)", lines[i].strip()):
            buf.append(_inline(lines[i].strip()))
            i += 1
        out.append("<p>" + " ".join(buf) + "</p>")
    return "\n".join(out), "<ul>" + "".join(toc) + "</ul>"


def _render(text: str) -> tuple[str, str]:
    if _markdown is not None:
        md = _markdown.Markdown(extensions=MD_EXTENSIONS)
        return md.convert(text), md.toc
    return _simple_markdown(text)


def doc_list(request):
    docs = _list_docs()
    groups: dict[str, list[dict]] = {}
    for d in docs:
        groups.setdefault(d["group"], []).append(d)
    return render(request, "docs/list.html", {"page_title": "문서", "groups": groups, "total": len(docs)})


def doc_detail(request, slug):
    path = _resolve(slug)
    body, toc = _render(path.read_text(encoding="utf-8"))
    return render(
        request,
        "docs/detail.html",
        {"page_title": path.stem, "slug": slug, "html": body, "toc": toc, "group": path.parent.name},
    )
