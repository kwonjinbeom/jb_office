"""워드프레스 jinbaam.com 글 모양 (2026-10-26 사용자: 기존 블로그처럼 카테고리마다 맞는 구조·CSS 꾸미기).

블록 에디터는 붙여 넣은 글의 인라인 style 을 지운다. 그래서 워드프레스는 style 대신 class 로 표시한 HTML 을
'사용자 정의 HTML' 블록 하나(<!-- wp:html -->)로 붙이고, 모양은 워드프레스 '추가 CSS'에 한 번 넣는
글모양 CSS(콘텐츠/블로그_카페/워드프레스/글모양.css)가 입힌다. 미리보기는 같은 CSS 를 <style> 로 함께 보여 준다.

모양(SiteCategory.look): wp_mountain(산과 캠핑) · wp_car(드라이브·자동차) · wp_travel(Korea Travel · World Travel).
원고·변환본의 마크다운에서 이렇게 바뀐다:
  맨 위 첫 인용(>)            → 리드 상자 (.jb-lead)
  ## 소제목 4개 이상           → 맨 위 목차 (.jb-toc, 영어 글은 Contents)
  ## Day 1 · … / ## 1일차 …   → 날짜 머리 (.jb-day)
  ::: 종류 | 이름 … :::       → 정보 카드 (.jb-card, 종류마다 머리 이름: CARD_KINDS)
  표                           → 가로로 밀리는 표 (.jb-table)
  사진 + 다음 줄 *출처*         → 사진과 캡션 (figure.jb-photo)
  ## 日本語まとめ · ## 中文简介 → 다른 언어 요약 상자 (.jb-lang)
  참고: · Sources:             → 작은 출처 줄 (.jb-source)
"""
import html
import re
from pathlib import Path

import markdown
from django.conf import settings

LOOKS = {"wp_mountain": "mountain", "wp_car": "car", "wp_travel": "travel"}
CSS_PATH = ("콘텐츠", "블로그_카페", "워드프레스", "글모양.css")

# 정보 카드 종류 → 머리 이름. 영어 글은 영어 종류를 쓴다.
CARD_KINDS = {
    "장소": "가 볼 곳", "맛집": "맛집·카페", "작품": "작품 정보", "제품": "제품 정보",
    "코스": "등산 코스", "캠핑": "야영장", "나들이": "나들이", "차": "차 정보", "비용": "드는 돈", "요약": "한눈에", "점검": "점검",
    "Place": "Place", "Food": "Eat & Drink", "Stay": "Stay", "Route": "Getting There", "Tour": "Tour",
    "Cost": "Cost", "Info": "Good to Know",
}
KIND_CLASS = {"장소": "place", "맛집": "food", "작품": "work", "제품": "product", "코스": "course", "캠핑": "camp",
              "나들이": "outing", "요약": "summary", "점검": "check",
              "차": "car", "비용": "cost", "Place": "place", "Food": "food", "Stay": "stay", "Route": "route", "Tour": "tour",
              "Cost": "cost", "Info": "info"}
CARD = re.compile(r"^:::[ \t]*(?P<kind>" + "|".join(map(re.escape, CARD_KINDS)) + r")[ \t]*\|[ \t]*(?P<name>[^\n]+?)[ \t]*\n"
                  r"(?P<rows>.*?)\n:::[ \t]*$", re.M | re.S)
_LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)")
_BOLD = re.compile(r"\*\*(?=\S)([^*\n]+?)(?<=\S)\*\*")
LANG_HEADS = ("日本語まとめ", "中文简介", "中文簡介")
SOURCE_P = re.compile(r"<p>(?=\s*(?:<strong>)?\s*(?:참고|Sources?|출처)\s*(?:</strong>)?\s*[:：])")
TOC_MIN = 4


def css() -> str:
    path = Path(settings.REPO_ROOT).joinpath(*CSS_PATH)
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _inline(text: str) -> str:
    out, last = [], 0
    for m in _LINK.finditer(text):
        out.append(html.escape(text[last:m.start()], quote=False))
        out.append(f'<a href="{html.escape(m.group(2), quote=True)}" target="_blank" rel="noopener">{html.escape(m.group(1), quote=False)}</a>')
        last = m.end()
    out.append(html.escape(text[last:], quote=False))
    return _BOLD.sub(r"<strong>\1</strong>", "".join(out))


def _card(m: re.Match) -> str:
    kind = m["kind"]
    rows = []
    for line in m["rows"].split("\n"):
        if not line.strip():
            continue
        label, sep, value = line.partition("|")
        if not sep:
            label, value = "", line
        rows.append(f"<div><dt>{_inline(label.strip())}</dt><dd>{_inline(value.strip())}</dd></div>")
    return (f'\n\n<div class="jb-card jb-card--{KIND_CLASS[kind]}"><div class="jb-card__head">'
            f'<span class="jb-card__kind">{CARD_KINDS[kind]}</span><strong class="jb-card__name">{_inline(m["name"])}</strong></div>'
            f'<dl class="jb-card__rows">{"".join(rows)}</dl></div>\n\n')  # 앞뒤 빈 줄: 마크다운이 HTML 덩어리로 둔다


IMAGE_BLOCK = re.compile(r"<p>\s*<img ([^>]*?)\s*/?>\s*(?:(?:<br\s*/?>)?\s*<em>(.*?)</em>\s*)?</p>(?:\s*<p><em>(.*?)</em></p>)?", re.S)


def _image(m: re.Match) -> str:
    attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
    caption = m.group(2) or m.group(3)
    img = f'<img src="{attrs.get("src", "")}" alt="{attrs.get("alt", "")}" loading="lazy">'
    return f'<figure class="jb-photo">{img}' + (f"<figcaption>{caption}</figcaption>" if caption else "") + "</figure>"


def _slug(text: str, used: set) -> str:
    base = re.sub(r"[^\w가-힣ぁ-んァ-ン一-龥]+", "-", html.unescape(re.sub(r"<[^>]+>", "", text))).strip("-").lower()[:40] or "s"
    slug, n = base, 2
    while slug in used:
        slug, n = f"{base}-{n}", n + 1
    used.add(slug)
    return slug


def _headings(out: str, english: bool) -> str:
    """소제목에 id · 날짜 머리 · 다른 언어 요약 표시, 소제목이 많으면 맨 위(리드 다음)에 목차."""
    used, toc = set(), []

    def h2(m):
        inner = m.group(1)
        text = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        slug = _slug(text, used)
        if any(text.startswith(h) for h in LANG_HEADS):
            return f'<h2 id="{slug}" class="jb-lang-head">{inner}</h2>'
        toc.append((slug, inner))
        cls = ' class="jb-day"' if re.match(r"(Day\s*\d+|\d+\s*일차)", text, re.I) else ""
        return f'<h2 id="{slug}"{cls}>{inner}</h2>'

    out = re.sub(r"<h2>(.*?)</h2>", h2, out, flags=re.S)
    out = _wrap_lang(out)
    if len(toc) >= TOC_MIN:
        items = "".join(f'<li><a href="#{s}">{i}</a></li>' for s, i in toc)
        nav = f'<nav class="jb-toc"><p class="jb-toc__title">{"Contents" if english else "목차"}</p><ul>{items}</ul></nav>'
        lead = re.search(r"</blockquote>", out)
        out = out[:lead.end()] + nav + out[lead.end():] if lead and out.lstrip().startswith("<blockquote") else nav + out
    return out


def _wrap_lang(out: str) -> str:
    """## 日本語まとめ · ## 中文简介 소제목부터 다음 소제목 앞까지를 요약 상자로."""
    parts = re.split(r'(?=<h2 id="[^"]*" class="jb-lang-head">)', out)
    for i, part in enumerate(parts):
        if part.startswith('<h2 id="') and 'class="jb-lang-head"' in part.split(">", 1)[0]:
            head_end = part.index("</h2>") + 5
            rest = part[head_end:]
            nxt = re.search(r"<h2\b", rest)
            body, after = (rest[:nxt.start()], rest[nxt.start():]) if nxt else (rest, "")
            parts[i] = f'<section class="jb-lang">{part[:head_end]}{body}</section>{after}'
    return "".join(parts)


def render(text: str, look: str = "") -> str:
    """원고·변환본 마크다운 → 워드프레스에 붙일 class HTML (바깥 <div class="jb-post jb-<모양>">)."""
    text = re.sub(r"<!--.*?-->", "", (text or "").replace("\r\n", "\n"), flags=re.S)
    english = not re.search(r"[가-힣]", re.sub(r"## (日本語まとめ|中文简介).*", "", text, flags=re.S)[:4000])
    out = markdown.markdown(CARD.sub(_card, text), extensions=["tables", "sane_lists"])
    out = re.sub(r"<blockquote>", '<blockquote class="jb-lead">', out, count=1)
    out = re.sub(r"<table>", '<div class="jb-table"><table>', out).replace("</table>", "</table></div>")
    out = IMAGE_BLOCK.sub(_image, out)
    out = SOURCE_P.sub('<p class="jb-source">', out)
    out = re.sub(r"<hr\s*/?>", '<hr class="jb-hr">', out)
    out = _headings(out, english)
    theme = LOOKS.get(look, "")
    return f'<div class="jb-post{" jb-" + theme if theme else ""}" lang="{"en" if english else "ko"}">\n{out}\n</div>'


def paste_html(text: str, look: str = "") -> str:
    """붙여넣기용: 블록 에디터의 코드 편집기에 붙이면 '사용자 정의 HTML' 블록 하나가 된다."""
    return f"<!-- wp:html -->\n{render(text, look)}\n<!-- /wp:html -->"


def preview_html(text: str, look: str = "") -> str:
    return f"<style>{css()}</style>\n{render(text, look)}"


PROMPT = """## 워드프레스 글 모양 (붙여 넣는 HTML 이 그린다 · 변환본에는 꾸밈 코드를 넣지 않는다)
- 마크다운 그대로 둔다. 맨 위 첫 인용(>)은 리드 상자, ## 소제목이 4개 이상이면 맨 위 목차가 저절로 생긴다.
- 정보 카드 `::: 종류 | 이름` … `:::` — 종류: 요약(한눈에) · 장소 · 맛집 · 코스(등산) · 캠핑(야영장) · 나들이 · 차 · 비용 · 점검 · 제품 / 영어 글은 Place · Food · Stay · Route · Tour · Cost · Info. 한 줄에 `이모지 이름표 | 값`.
- 여행 일정은 `## Day 1 · 지역` (한국어는 `## 1일차 · 지역`) 이 날짜 머리가 된다.
- Korea Travel 은 끝에 `## 日本語まとめ` · `## 中文简介` 소제목으로 요약 — 요약 상자로 그려진다.
- 사진은 `![설명](주소)` + 다음 줄 `*Photo: 작가 · 출처*` (한국어 글은 `*사진: …*`). 맨 끝 출처 줄은 `참고:` (영어는 `Sources:`)."""
