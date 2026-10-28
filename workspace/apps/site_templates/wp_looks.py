"""워드프레스 jinbaam.com 글 모양 (2026-10-26 사용자: 기존 블로그처럼 카테고리마다 맞는 구조·CSS 꾸미기).

블록 에디터는 붙여 넣은 글의 인라인 style 을 지운다. 그래서 워드프레스는 style 대신 class 로 표시한 HTML 을
'사용자 정의 HTML' 블록 하나(<!-- wp:html -->)로 붙이고, 모양은 글모양 CSS(콘텐츠/블로그_카페/워드프레스/글모양.css)가 입힌다.
그 CSS 는 블록 안에 <style> 로 함께 넣는다 (2026-10-26 사용자: 붙였더니 글꼴·색이 다 깨졌다 — '추가 CSS'가 아직 없었고,
추가 CSS 는 글 편집 화면에는 보이지 않는다). 관리자 계정은 <style> 이 남는다. 미리보기도 같은 CSS 로 보여 준다.

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
여행(wp_travel)만 더 (2026-10-28 사용자: 미리캔버스 '주황 심플 이탈리아 여행'처럼 — 티켓 · 점선 · 탭 라벨):
  ## Day 1 · 지역              → 탑승권 머리 (.jb-day__no DAY 01 + .jb-day__main, 'Friday 6 Nov: 지역' 이면 날짜는 작은 줄)
  | Time | Stop | … | 표       → 점선 타임라인 (ol.jb-time)
  ::: Route | A → B            → 카드 안 경로선 A ····✈···· B (.jb-route)
  ## FAQ 아래 질문             → 질문 탭 + 답 판 (.jb-faq) — ### 질문 이든 **질문** 이든
  - [ ] 목록 · Checklist 목록  → 체크 목록 (ul.jb-check)
  카드 줄 머리의 이모지         → 뺀다 (글자만, 탭 라벨에 선 아이콘)
  영어 글로 본다 (본문에 한글 장소 이름이 있어도 Contents · lang=en)
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


def css_min() -> str:
    """글마다 붙이는 <style> 용: 주석·빈칸을 걷어 짧게."""
    out = re.sub(r"/\*.*?\*/", "", css(), flags=re.S)
    out = re.sub(r"\s+", " ", out)
    return re.sub(r"\s*([{};,>])\s*", r"\1", out).replace(";}", "}").strip()


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


DAY = re.compile(r"(Day\s*\d+|\d+\s*일차)", re.I)
DAY_PARTS = re.compile(r"^\s*(?:Day\s*(\d+)|(\d+)\s*일차)\s*[·:\-–—]?\s*(.*)$", re.I | re.S)


def _ticket(inner: str, total: int) -> str:
    """여행 날짜 머리 → 탑승권: 왼쪽 DAY 01, 오른쪽 작은 줄(날짜 · Day 1 of 2)과 지역."""
    m = DAY_PARTS.match(inner)
    n = int(m.group(1) or m.group(2))
    rest, date = m.group(3).strip(), ""
    head, sep, tail = rest.partition(": ")
    if sep and len(re.sub(r"<[^>]+>", "", head)) <= 24 and tail.strip():
        date, rest = head.strip(), tail.strip()
    small = (f"{date} · " if date else "") + f"Day {n} of {total}"
    return (f'<span class="jb-day__no"><small>DAY</small>{n:02d}</span>'
            f'<span class="jb-day__main"><small>{small}</small>{rest or f"Day {n}"}</span>')


def _headings(out: str, english: bool, travel: bool = False) -> str:
    """소제목에 id · 날짜 머리 · 다른 언어 요약 표시, 소제목이 많으면 맨 위(리드 다음)에 목차."""
    used, toc = set(), []
    total = sum(1 for t in re.findall(r"<h2>(.*?)</h2>", out, re.S) if DAY.match(re.sub(r"<[^>]+>", "", t).strip()))

    def h2(m):
        inner = m.group(1)
        text = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        slug = _slug(text, used)
        if any(text.startswith(h) for h in LANG_HEADS):
            return f'<h2 id="{slug}" class="jb-lang-head">{inner}</h2>'
        toc.append((slug, inner))
        if not DAY.match(text):
            return f'<h2 id="{slug}">{inner}</h2>'
        return f'<h2 id="{slug}" class="jb-day">{_ticket(inner, total) if travel else inner}</h2>'

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


_CELL = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)
TIME_TABLE = re.compile(r'<div class="jb-table"><table>\s*<thead>\s*<tr>\s*<th[^>]*>\s*(?:Time|시간)\s*</th>(.*?)</tr>\s*</thead>'
                        r"\s*<tbody>(.*?)</tbody>\s*</table></div>", re.S | re.I)
EMPTY = {"", "—", "–", "-"}


def _timeline(m: re.Match) -> str:
    """| Time | Stop | Time there | Move | 표 → 점선 타임라인. 셋째 칸부터는 머리 이름으로 머무는 시간 · 이동을 가른다."""
    heads = [re.sub(r"<[^>]+>", "", h).strip() for h in _CELL.findall(m.group(1))]
    items = []
    for row in re.findall(r"<tr>(.*?)</tr>", m.group(2), re.S):
        cells = [c.strip() for c in _CELL.findall(row)]
        if len(cells) < 2:
            continue
        meta = []
        for head, cell in zip(heads[1:], cells[2:]):
            if cell in EMPTY:
                continue
            kind = "move" if re.search(r"move|how|이동|교통", head, re.I) else "stay" if re.search(r"time|stay|시간|머무", head, re.I) else "note"
            meta.append(f'<span class="jb-time__{kind}">{cell}</span>')
        items.append(f'<li><time>{cells[0]}</time><div><b>{cells[1]}</b>{"".join(meta)}</div></li>')
    return f'<ol class="jb-time">{"".join(items)}</ol>' if items else m.group(0)


ROUTE_CARD = re.compile(r'(<div class="jb-card jb-card--route"><div class="jb-card__head">.*?<strong class="jb-card__name">)(.*?)(</strong></div>)', re.S)


def _route(m: re.Match) -> str:
    """::: Route | A → B → 카드 머리 아래 경로선 A ····✈···· B (괄호 안 설명은 경로선에서 뺀다)."""
    name = html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))
    if "→" not in name:
        return m.group(0)
    a, b = (html.escape(re.sub(r"\([^)]*\)", "", x).strip().upper(), quote=False) for x in name.split("→", 1))
    if not a or not b:
        return m.group(0)
    return f'{m.group(0)}<div class="jb-route"><b>{a}</b><i aria-hidden="true"></i><b>{b}</b></div>'


FAQ_HEAD = re.compile(r'(<h2 id="[^"]*">\s*(?:FAQ|Frequently Asked Questions|자주 묻는 질문)[^<]*</h2>)(.*?)(?=<h2\b|<section\b|<p class="jb-source"|\Z)', re.S | re.I)


_BOLD_Q = r"<p><strong>[^<]*\?</strong>"  # **질문?** 으로 시작하는 문단
_ANSWER = rf"(?:(?:<p>(?!<strong>[^<]*\?</strong>).*?</p>|<ul>.*?</ul>|<ol>.*?</ol>)\s*)*"
FAQ_ITEM = re.compile(rf"<h3[^>]*>(?P<q1>.*?)</h3>\s*(?P<a1>{_ANSWER})"
                      rf"|<p><strong>(?P<q2>[^<]*\?)</strong>\s*(?:<br\s*/?>)?\s*(?P<a2>.*?)</p>\s*(?P<a3>{_ANSWER})", re.S)


def _faq(m: re.Match) -> str:
    """## FAQ 아래 질문들 → 질문 탭 + 답 판. ### 질문 + 문단 이든, **질문?** 줄바꿈 답 이든 (섞여도 순서대로).
    질문 앞 소개 문단은 그대로 두고, 질문 사이에 틀에 안 맞는 것이 있으면 아무것도 바꾸지 않는다 (글이 빠지지 않게)."""
    body, items, pos, intro = m.group(2), [], None, ""
    for it in FAQ_ITEM.finditer(body):
        if pos is None:
            intro, pos = body[:it.start()], it.start()
        if body[pos:it.start()].strip():
            return m.group(0)
        if it["q1"] is not None:
            q, a = it["q1"], it["a1"].strip()
        else:
            q, a = it["q2"], ((f"<p>{it['a2'].strip()}</p>" if it["a2"].strip() else "") + it["a3"].strip())
        if not a:
            return m.group(0)
        items.append((q.strip(), a))
        pos = it.end()
    if not items or body[pos:].strip():
        return m.group(0)
    faq = "".join(f'<div class="jb-faq__item"><p class="jb-faq__q">{q}</p><div class="jb-faq__a">{a}</div></div>' for q, a in items)
    return f'{m.group(1)}{intro}<div class="jb-faq">{faq}</div>'


def _checklist(out: str) -> str:
    """- [ ] 목록 · Checklist 소제목 바로 아래 목록 → 체크 목록."""
    def ul(m):
        lis = re.findall(r"<li>(.*?)</li>", m.group(2), re.S)
        boxed = lis and all(re.match(r"\s*\[[ xX]\]", li) for li in lis)
        if not (boxed or m.group(1)):
            return m.group(0)
        body = re.sub(r"<li>\s*\[[ xX]\]\s*", "<li>", m.group(2))
        return f'{m.group(1) or ""}<ul class="jb-check">{body}</ul>'
    return re.sub(r'(<h2 id="[^"]*">[^<]*Checklist[^<]*</h2>\s*)?<ul>((?:(?!</?ul>).)*)</ul>', ul, out, flags=re.S | re.I)


def _travel(out: str) -> str:
    out = TIME_TABLE.sub(_timeline, out)
    out = ROUTE_CARD.sub(_route, out)
    out = FAQ_HEAD.sub(_faq, out)
    out = _checklist(out)
    return re.sub(r"<dt>[^\w<\[(]+", "<dt>", out)  # 카드 줄 머리 이모지 → 글자만


def render(text: str, look: str = "") -> str:
    """원고·변환본 마크다운 → 워드프레스에 붙일 class HTML (바깥 <div class="jb-post jb-<모양>">)."""
    text = re.sub(r"<!--.*?-->", "", (text or "").replace("\r\n", "\n"), flags=re.S)
    travel = look == "wp_travel"
    english = travel or not re.search(r"[가-힣]", re.sub(r"## (日本語まとめ|中文简介).*", "", text, flags=re.S)[:4000])
    out = markdown.markdown(CARD.sub(_card, text), extensions=["tables", "sane_lists"])
    out = re.sub(r"<blockquote>", '<blockquote class="jb-lead">', out, count=1)
    out = re.sub(r"<table>", '<div class="jb-table"><table>', out).replace("</table>", "</table></div>")
    out = IMAGE_BLOCK.sub(_image, out)
    out = SOURCE_P.sub('<p class="jb-source">', out)
    out = re.sub(r"<hr\s*/?>", '<hr class="jb-hr">', out)
    out = _headings(out, english, travel)
    if travel:
        out = _travel(out)
    theme = LOOKS.get(look, "")
    return f'<div class="jb-post{" jb-" + theme if theme else ""}" lang="{"en" if english else "ko"}">\n{out}\n</div>'


def paste_html(text: str, look: str = "") -> str:
    """붙여넣기용: 블록 에디터의 코드 편집기에 붙이면 '사용자 정의 HTML' 블록 하나가 된다."""
    return f"<!-- wp:html -->\n<style>{css_min()}</style>\n{render(text, look)}\n<!-- /wp:html -->"


def preview_html(text: str, look: str = "") -> str:
    return f"<style>{css()}</style>\n{render(text, look)}"


# 초안 올리기 (wp_draft 명령, 2026-10-26): 발췌는 맨 위 리드(첫 인용), 슬러그는 변환이 준 것 · 없으면 영어 제목에서.
EXCERPT_MAX = 300


def excerpt(text: str) -> str:
    """맨 위 첫 인용(>) 덩어리를 글자만으로. 리드가 없으면 첫 문단."""
    lines = re.sub(r"<!--.*?-->", "", (text or "").replace("\r\n", "\n"), flags=re.S).strip().split("\n")
    quote = []
    for line in lines:
        if line.startswith(">"):
            quote.append(line.lstrip("> ").strip())
        elif quote:
            break
    if not quote:
        quote = next((p.split("\n") for p in "\n".join(lines).split("\n\n")
                      if p.strip() and not p.lstrip().startswith(("#", "!", "|", ":::", "<"))), [])
    out = " ".join(q for q in quote if q)
    out = _LINK.sub(r"\1", out)
    out = re.sub(r"[*_`]+", "", out).strip()
    return out if len(out) <= EXCERPT_MAX else out[:EXCERPT_MAX - 1].rsplit(" ", 1)[0] + "…"


def clean_slug(slug: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (slug or "").strip().lower()).strip("-")
    return slug[:80].rsplit("-", 1)[0] if len(slug) > 80 else slug


def auto_slug(title: str) -> str:
    """영어 제목이면 앞 8단어로 (괄호 속 날짜 등은 뺀다). 한글 제목은 '' — 변환이 슬러그를 줘야 한다."""
    if re.search(r"[가-힣]", title or ""):
        return ""
    words = clean_slug(re.sub(r"\(.*?\)", " ", title or "")).split("-")
    return "-".join(w for w in words if w)[:80].strip("-") if len(words) <= 8 else "-".join(words[:8])


PROMPT = """## 워드프레스 글 모양 (붙여 넣는 HTML 이 그린다 · 변환본에는 꾸밈 코드를 넣지 않는다)
- 마크다운 그대로 둔다. 맨 위 첫 인용(>)은 리드 상자, ## 소제목이 4개 이상이면 맨 위 목차가 저절로 생긴다.
- 정보 카드 `::: 종류 | 이름` … `:::` — 종류: 요약(한눈에) · 장소 · 맛집 · 코스(등산) · 캠핑(야영장) · 나들이 · 차 · 비용 · 점검 / 영어 글은 Place · Food · Stay · Route · Tour · Cost · Info. 한 줄에 `이모지 이름표 | 값`.
- 여행 일정은 `## Day 1 · 지역` (한국어는 `## 1일차 · 지역`) 이 날짜 머리가 된다.
- Korea Travel · World Travel 은 '주황 티켓' 모양 (2026-10-28 사용자) — 아래처럼 쓰면 변환 HTML 이 그린다:
  · `## Day 1 · 지역` → 탑승권 머리(DAY 01 + 지역). 날짜를 넣을 땐 `## Day 1 · Friday 6 Nov: 지역` (콜론 앞이 작은 줄).
  · 그 아래 시간 표는 첫 칸을 `Time` 으로 (`| Time | Stop | Time there | Move |`) → 점선 타임라인. 빈 칸은 `—`.
  · `::: Route | 출발 → 도착` 은 꼭 `→` 로 (`to` 금지) → 카드 안에 출발 ····✈···· 도착 경로선. 괄호 설명은 선에서 빠진다.
  · 카드 줄 머리 이모지는 화면에서 빠진다 — 이름표(Hours, Admission …)만으로 뜻이 통하게.
  · `## FAQ` 아래는 `### 질문` + 답 한두 문장 → 질문 탭 + 답 판. `## Entry & Money Checklist` 는 `- [ ] 항목` 목록 → 체크 목록.
- Korea Travel 은 끝에 `## 日本語まとめ` · `## 中文简介` 소제목으로 요약 — 요약 상자로 그려진다.
- 사진은 `![설명](주소)` + 다음 줄 `*Photo: 작가 · 출처*` (한국어 글은 `*사진: …*`). 맨 끝 출처 줄은 `참고:` (영어는 `Sources:`).
- 맨 위 첫 인용(리드)이 워드프레스 '요약(발췌)'이 되고, 본문 첫 사진이 대표 이미지가 된다 — 리드는 카테고리 컨셉대로 2~3문장, 첫 사진은 글을 대표하는 것으로.
- 슬러그: 영문 소문자와 하이픈 3~6단어 (예: `mindungsan-silver-grass-hiking`, `kyoto-3-days-autumn-leaves`). 날짜·연도는 넣지 않는다."""
