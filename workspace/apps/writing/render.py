"""포스트 본문(마크다운) → 블로그에 그대로 붙여넣을 HTML.

붙여넣기용이라 표·인용·이미지·사진 자리 같은 꾸밈은 class 가 아니라 인라인 style 로 넣는다.
네이버 스마트에디터·티스토리 기본 모드는 붙여넣을 때 외부 CSS 를 버리고 인라인 style 만 남기기 때문이다.
형식은 포스팅 자동화 시험 원고의 붙여넣기.html 과 같다 (콘텐츠/블로그_카페/포스팅자동화/원고/).

본문에서 쓰는 줄 단위 표시 (줄 맨 앞에 쓴다):
  [사진] 설명   → 빨간 점선 상자: 내 사진을 올릴 자리 (📷 로 시작해도 된다)
  [그림] 파일명 → 파란 점선 상자: 준비한 그림을 올릴 자리 (🖼 로 시작해도 된다)
  [캡션] 문장   → 사진·그림 아래 가운데 회색 한 줄
그 밖에는 일반 마크다운: ## 소제목, **굵게**, - 목록, 1. 번호, > 인용, | 표 |, ---
이미지: ![설명](https://주소) 는 실제 이미지, ![설명](그림1.png) 처럼 파일 이름이면 파란 상자(그림 올릴 자리).
       이미지 바로 다음 줄을 *기울임* 한 줄로 쓰면 캡션이 된다 (시험 원고 원고.md 의 형식).
줄바꿈 한 번은 그대로 줄바꿈, 빈 줄은 문단 나눔이다 (블로그 에디터에서 쓰는 감각 그대로).
"""
import html
import re
from html.parser import HTMLParser

import markdown

SLOT_STYLE = {
    "photo": "margin:18px 0;padding:14px;border:1px dashed #fca5a5;border-radius:8px;background:#fef2f2;"
             "text-align:center;color:#374151;font-size:14px",
    "figure": "margin:18px 0;padding:14px;border:1px dashed #93c5fd;border-radius:8px;background:#eff6ff;"
              "text-align:center;color:#374151;font-size:14px",
}
CAPTION_STYLE = "text-align:center;color:#6b7280;font-size:14px;margin-top:-8px"
TABLE_STYLE = "border-collapse:collapse;width:100%;font-size:15px"
CELL_STYLE = "border:1px solid #d1d5db;padding:8px"
HEAD_STYLE = "border:1px solid #d1d5db;background:#f3f4f6;padding:8px"
HOT_CELL_STYLE = CELL_STYLE + ";background:#fff4e5"  # 🔥 로 시작하는 표 줄 (화제 종목 등, 2026-10-22 사용자)
QUOTE_STYLE = "margin:18px 0;padding:12px 16px;border-left:4px solid #d1d5db;background:#f9fafb;color:#374151"
HR_STYLE = "border:0;border-top:1px solid #e5e7eb;margin:28px 0"
IMG_STYLE = "max-width:100%;height:auto"

# [사진] 설명 · [사진: 설명] (변환 요청문이 쓰는 꼴) · 📷 설명
LINE_MARK = re.compile(r"^\s*(?:>\s*)?(?:\[(?P<kind>사진|그림|캡션)(?:\s*[:：]\s*(?P<inner>[^\]]*))?\]|(?P<emoji>📷|🖼️?))"
                       r"\s*[:：]?\s*(?P<rest>.*)$")


def _mark_lines(text: str) -> str:
    """[사진]·[그림]·[캡션] 줄을 인라인 style 을 단 HTML 문단으로 바꾼다. 마크다운은 이 줄을 건드리지 않는다."""
    out = []
    for line in text.split("\n"):
        m = LINE_MARK.match(line)
        if not m:
            out.append(line)
            continue
        kind = m["kind"] or ("사진" if m["emoji"] == "📷" else "그림")
        body = html.escape(" ".join(t for t in (m["inner"], m["rest"]) if t and t.strip()).strip())
        if kind == "캡션":
            block = f'<p style="{CAPTION_STYLE}">{body}</p>'
        elif kind == "사진":
            block = f'<p class="wr-slot" style="{SLOT_STYLE["photo"]}">📷 {body or "여기에 내 사진 올리기"}</p>'
        else:
            block = f'<p class="wr-slot" style="{SLOT_STYLE["figure"]}">🖼 여기에 그림 올리기{": <strong>" + body + "</strong>" if body else ""}</p>'
        out.extend(["", block, ""])
    return "\n".join(out)


# 정보 카드 (2026-10-23 사용자: 갈 곳·작품의 입장 마감·입장료·출연·러닝타임 같은 정보는 서술하지 말고 보기 쉽게 —
# 시간표 표와는 완전히 다른 디자인으로, 앞으로 같은 유형에 똑같이). 원고·변환본에 이렇게 쓴다:
#   ::: 장소 | 오죽헌
#   ⏰ 관람 | 09:00~18:00
#   🎫 예약 | [공식 안내](https://…)
#   :::
# 종류마다 색 하나: 장소(지역 놀거리·축제) · 맛집(카페·식당) · 작품(영화·OTT) · 제품(출시).
# 칸 합치기 없이 두 칸 표로 그린다 — 네이버·티스토리에 붙여도 표·칸 바탕색·글자색이 남는다 (칸 합치기는 네이버에서 깨진다).
CARD_KINDS = {  # 종류: (머리 칸 이름, 진한 색, 연한 바탕, 테두리)
    "장소": ("가 볼 곳", "#1f6f5c", "#eef6f2", "#cfe3da"),
    "맛집": ("맛집·카페", "#a4501d", "#fcf3ec", "#efd9c7"),
    "작품": ("작품 정보", "#3b3a8c", "#f0f0fa", "#d7d7ef"),
    "제품": ("제품 정보", "#24527a", "#edf3f9", "#cddcea"),
}
CARD_TABLE_STYLE = "border-collapse:collapse;width:100%;font-size:15px;margin:18px 0"


def _card_styles(kind: str) -> dict:
    _, dark, tint, line = CARD_KINDS[kind]
    return {
        "head_label": f"border:1px solid {dark};background-color:{dark};color:#ffffff;padding:10px 12px;"
                      "font-size:13px;font-weight:bold;text-align:center;width:28%",
        "head_name": f"border:1px solid {dark};background-color:{dark};color:#ffffff;padding:10px 14px;"
                     "font-size:16px;font-weight:bold;text-align:left",
        "label": f"border:1px solid {line};background-color:{tint};color:{dark};padding:9px 12px;"
                 "font-weight:bold;text-align:left;width:28%",
        "value": f"border:1px solid {line};background-color:#ffffff;color:#333333;padding:9px 14px;text-align:left",
    }


CARD_STYLES = {s for kind in CARD_KINDS for s in _card_styles(kind).values()} | {CARD_TABLE_STYLE}
CARD = re.compile(r"^:::[ \t]*(?P<kind>장소|맛집|작품|제품)[ \t]*\|[ \t]*(?P<name>[^\n]+?)[ \t]*\n(?P<rows>.*?)\n:::[ \t]*$",
                  re.M | re.S)
_CARD_LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)")


def _card_inline(text: str) -> str:
    """카드 칸 안의 글: 이스케이프하고 [글](주소) 링크와 **굵게** 만 살린다 (마크다운 변환기는 HTML 표 안을 보지 않는다)."""
    out, last = [], 0
    for m in _CARD_LINK.finditer(text):
        out.append(html.escape(text[last:m.start()], quote=False))
        out.append(f'<a href="{html.escape(m.group(2), quote=True)}">{html.escape(m.group(1), quote=False)}</a>')
        last = m.end()
    out.append(html.escape(text[last:], quote=False))
    return BOLD.sub(r"<strong>\1</strong>", "".join(out))


def _card(m: re.Match) -> str:
    kind, s = m["kind"], _card_styles(m["kind"])
    rows = [f'<tr><td style="{s["head_label"]}">{CARD_KINDS[kind][0]}</td>'
            f'<td style="{s["head_name"]}">{_card_inline(m["name"])}</td></tr>']
    for line in m["rows"].split("\n"):
        label, sep, value = line.partition("|")
        if not line.strip():
            continue
        if not sep:  # 이름표 없는 줄은 앞 줄 값에 이어 쓴 것
            label, value = "", line
        rows.append(f'<tr><td style="{s["label"]}">{_card_inline(label.strip())}</td>'
                    f'<td style="{s["value"]}">{_card_inline(value.strip())}</td></tr>')
    return f'\n<table style="{CARD_TABLE_STYLE}"><tbody>{"".join(rows)}</tbody></table>\n'


def cards(text: str) -> str:
    """::: 종류 | 이름 … ::: 덩어리를 정보 카드 표(HTML)로. 마크다운 변환 전에 부른다."""
    return CARD.sub(_card, text)


BOLD = re.compile(r"\*\*(?=\S)([^*\n]+?)(?<=\S)\*\*")


def fix_bold(text: str) -> str:
    """**굵게** 를 <strong> 으로 먼저 바꾼다. 마크다운 변환기는 **"따옴표"**는 · **10%**를 처럼
    문장부호로 끝나고 바로 한글 조사가 붙으면 굵게로 보지 않아 ** 가 글자로 남는다. 코드(`…`, ```)는 건드리지 않는다."""
    out, fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
        if not fence:
            parts = re.split(r"(`[^`]*`)", line)
            line = "".join(p if p.startswith("`") else BOLD.sub(r"<strong>\1</strong>", p) for p in parts)
        out.append(line)
    return "\n".join(out)


def _cell(tag: str, align: str | None) -> str:
    base = HEAD_STYLE if tag == "th" else CELL_STYLE
    return f'<{tag} style="{base};text-align:{align or "left"}">'


def _flatten_header(out: str) -> str:
    """머리글 줄(<thead>·<th>)을 굵은 글씨 + 회색 바탕의 보통 칸으로 바꾼다.
    티스토리 기본 모드에 붙여넣으면 <thead>/<th> 줄이 통째로 표 밖 한 줄 글로 빠진다 (2026-10-15 실제 편집기로 확인).
    보통 칸(td) + <strong> + background 는 그대로 남는다."""
    out = re.sub(r"<thead>\s*", "<tbody>", out)
    out = re.sub(r"\s*</thead>\s*<tbody>", "", out)
    out = out.replace("</thead>", "</tbody>")

    def head_cell(m: re.Match) -> str:
        inner = m.group(2)
        if not re.fullmatch(r"\s*<strong>.*</strong>\s*", inner, re.S) and inner.strip():
            inner = f"<strong>{inner}</strong>"
        return f"<td{m.group(1)}>{inner}</td>"

    return re.sub(r"<th(\s[^>]*)?>(.*?)</th>", head_cell, out, flags=re.S)


HOT_ROW = re.compile(r"<tr>\s*<td[^>]*>\s*(?:<strong>\s*)?🔥.*?</tr>", re.S)


def _hot_rows(out: str) -> str:
    """첫 칸이 🔥 로 시작하는 표 줄은 칸마다 연한 주황 바탕 (공모주 화제 종목 등, 2026-10-22 사용자: 색을 칠해 줘)."""
    plain = f'style="{CELL_STYLE};text-align:'
    return HOT_ROW.sub(lambda m: m.group(0).replace(plain, f'style="{HOT_CELL_STYLE};text-align:'), out)


# 문단 하나에 이미지만 있는 것 + 바로 뒤 기울임(*문장*) 한 줄 = 이미지와 캡션
IMAGE_BLOCK = re.compile(
    r"<p>\s*<img ([^>]*?)\s*/?>\s*(?:<br\s*/?>\s*<em>(.*?)</em>\s*)?</p>(?:\s*<p><em>(.*?)</em></p>)?", re.S
)


def _image(m: re.Match) -> str:
    attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
    src, alt = attrs.get("src", ""), attrs.get("alt", "")
    caption = m.group(2) or m.group(3)
    if re.match(r"(https?:)?//|data:image/", src):
        out = f'<p style="text-align:center;margin:18px 0"><img src="{src}" alt="{alt}" style="{IMG_STYLE}"></p>'
    else:
        # 인터넷 주소가 아닌 파일 이름(그림1.png) → 붙여넣은 뒤 그 파일을 올릴 자리
        name = src.rsplit("/", 1)[-1]
        out = f'<p class="wr-slot" style="{SLOT_STYLE["figure"]}">🖼 여기에 그림 올리기: <strong>{name}</strong></p>'
    if caption:
        out += f'\n<p style="{CAPTION_STYLE}">{caption}</p>'
    return out


# ---------------------------------------------------------------------------
# 글쓰기 편집기(기본모드)가 저장하는 HTML. 붙여넣은 웹 문서의 찌꺼기·위험한 것을 걸러 낸다.
# ---------------------------------------------------------------------------
HTML_START = re.compile(r"^\s*<(p|h[1-6]|ul|ol|table|blockquote|hr|div|img|figure|br)\b", re.I)
ALLOWED_TAGS = {"p", "br", "h2", "h3", "h4", "strong", "em", "u", "s", "ul", "ol", "li", "blockquote",
                "table", "thead", "tbody", "tr", "th", "td", "hr", "a", "img", "code"}
RENAME_TAGS = {"b": "strong", "i": "em", "strike": "s", "del": "s", "h1": "h2", "h5": "h4", "h6": "h4", "div": "p"}
BLOCK_TAGS = {"p", "h2", "h3", "h4", "ul", "ol", "table", "blockquote", "hr"}
DROP_WITH_CONTENT = {"script", "style", "iframe", "object", "embed", "head", "title", "noscript", "template", "svg"}
VOID_TAGS = {"br", "hr", "img"}
STYLED_TAGS = {"p", "h2", "h3", "h4", "blockquote", "table", "th", "td", "hr", "img"}
ALIGN_STYLE = re.compile(r"^\s*text-align:\s*(left|center|right|justify)\s*;?\s*$")


def _known_styles() -> set[str]:
    """이 도구가 직접 다는 style 만 남긴다. 웹 문서에서 붙여 온 글꼴·색 같은 꾸밈은 버린다."""
    base = {*SLOT_STYLE.values(), CAPTION_STYLE, TABLE_STYLE, QUOTE_STYLE, HR_STYLE, IMG_STYLE,
            "text-align:center;margin:18px 0"}
    cells = {f"{b};text-align:{a}" for b in (CELL_STYLE, HEAD_STYLE, HOT_CELL_STYLE) for a in ("left", "center", "right")}
    return {s.replace(" ", "") for s in base | cells | CARD_STYLES | {CELL_STYLE, HEAD_STYLE}}


KNOWN_STYLES = _known_styles()


def _style_ok(value: str) -> bool:
    return bool(ALIGN_STYLE.match(value)) or value.replace(" ", "").rstrip(";") in KNOWN_STYLES
SAFE_URL = re.compile(r"^(https?:|mailto:|#|/)", re.I)


def is_html(text: str) -> bool:
    """편집기에서 저장한 본문(HTML)인지, 예전·Claude 원고(마크다운)인지."""
    return bool(HTML_START.match(text or ""))


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.stack: list[str] = []
        self.skip = 0  # DROP_WITH_CONTENT 안에 있는 깊이

    def handle_starttag(self, tag, attrs):
        tag = RENAME_TAGS.get(tag, tag)
        if tag in DROP_WITH_CONTENT:
            self.skip += 1
            return
        if self.skip or tag not in ALLOWED_TAGS:
            return  # 모르는 태그(span, font …)는 벗기고 안의 글만 남긴다
        if tag in BLOCK_TAGS and "p" in self.stack and "li" not in self.stack and "td" not in self.stack and "th" not in self.stack:
            # 문단 안에 문단·표가 열리면(div 를 p 로 바꾼 경우 등) 앞 문단을 먼저 닫는다
            self.handle_endtag("p")
        kept = []
        for name, value in attrs:
            value = value or ""
            if name == "style" and tag in STYLED_TAGS and _style_ok(value):
                kept.append((name, value))
            elif name == "class" and tag == "p" and value == "wr-slot":
                kept.append((name, value))
            elif name == "href" and tag == "a" and SAFE_URL.match(value.strip()):
                kept.append((name, value.strip()))
            elif name == "src" and tag == "img" and re.match(r"^(https?:)?//", value.strip()):
                kept.append((name, value.strip()))
            elif name == "alt" and tag == "img":
                kept.append((name, value))
            elif name in ("colspan", "rowspan") and tag in ("th", "td") and value.isdigit():
                kept.append((name, value))
        if tag == "img" and not any(n == "src" for n, _ in kept):
            return  # 주소가 없거나 위험한 이미지는 뺀다
        attr_text = "".join(f' {n}="{html.escape(v, quote=True)}"' for n, v in kept)
        if tag == "a":
            attr_text += ' target="_blank" rel="noopener"'
        self.out.append(f"<{tag}{attr_text}>")
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = RENAME_TAGS.get(tag, tag)
        if tag in DROP_WITH_CONTENT:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag not in ALLOWED_TAGS or tag in VOID_TAGS or tag not in self.stack:
            return
        while self.stack:  # 안 닫힌 안쪽 태그까지 같이 닫는다
            open_tag = self.stack.pop()
            self.out.append(f"</{open_tag}>")
            if open_tag == tag:
                break

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data, quote=False))

    def result(self) -> str:
        while self.stack:
            self.out.append(f"</{self.stack.pop()}>")
        return "".join(self.out)


def clean_html(text: str) -> str:
    cleaner = _Cleaner()
    cleaner.feed(re.sub(r"<!--.*?-->", "", text or "", flags=re.S))
    cleaner.close()
    return re.sub(r"<p>\s*</p>", "", cleaner.result()).strip()


def text_to_html(text: str) -> str:
    """서식 없는 글: 빈 줄은 문단, 줄바꿈 한 번은 <br>."""
    blocks = [b for b in re.split(r"\n\s*\n", (text or "").replace("\r\n", "\n").strip()) if b.strip()]
    return "".join("<p>" + html.escape(b).replace("\n", "<br>") + "</p>" for b in blocks)


def _decorate(out: str) -> str:
    """꾸밈 없는 표·인용·구분선·이미지에 붙여넣기용 인라인 style 을 단다. 이미 style 이 있으면 그대로 둔다."""
    out = out.replace("<table>", f'<table style="{TABLE_STYLE}">')
    out = re.sub(r'<(th|td)(?: style="text-align: (\w+);")?>', lambda m: _cell(m.group(1), m.group(2)), out)
    out = _hot_rows(_flatten_header(out))
    out = out.replace("<blockquote>", f'<blockquote style="{QUOTE_STYLE}">')
    out = re.sub(r"<hr\s*/?>", f'<hr style="{HR_STYLE}">', out)
    out = IMAGE_BLOCK.sub(_image, out)
    return out


def render_body(text: str) -> str:
    """본문 → 블로그에 붙여넣을 HTML. 편집기 HTML 이면 걸러 내고, 마크다운이면 변환한다."""
    if is_html(text):  # 편집기 글·HTML 로 저장한 변환본도 확인 날짜는 같게
        return quote_as_body(soft_check_dates(_decorate(clean_html(text))))
    text = re.sub(r"<!--.*?-->", "", (text or "").replace("\r\n", "\n"), flags=re.S)
    out = _decorate(markdown.markdown(fix_bold(_mark_lines(cards(text))), extensions=["tables", "sane_lists", "nl2br"]))
    return quote_as_body(soft_check_dates(clean_html(out)))  # 마크다운 안에 섞인 날 HTML 도 같은 기준으로 거른다


# 인용 상자(맨 위 결론 등)를 본문과 같은 글꼴로 (2026-10-21 사용자: 티스토리에서만 글꼴이 달랐다).
# 티스토리는 그냥 <blockquote> 를 기본 인용(style1: 가운데 정렬 · 명조)으로 바꾸고 스킨이 그 글꼴을 입힌다.
# → 세로줄 인용(style2)으로 표시하고, 글꼴·크기·줄간격은 본문을 따르게(inherit), 왼쪽 정렬을 인라인으로 박는다.
QUOTE_FONT = "font-family:inherit;font-size:inherit;line-height:inherit;font-style:normal;text-align:left"
_QUOTE_BLOCK = re.compile(r'<blockquote style="' + re.escape(QUOTE_STYLE) + r'">(.*?)</blockquote>', re.S)


def quote_as_body(body_html: str) -> str:
    def one(m: re.Match) -> str:
        inner = re.sub(r"<p>", f'<p style="{QUOTE_FONT}">', m.group(1))
        return f'<blockquote data-ke-style="style2" style="{QUOTE_STYLE};{QUOTE_FONT}">{inner}</blockquote>'
    return _QUOTE_BLOCK.sub(one, body_html)


# 출처 줄 끝의 확인 날짜: "2026년 10월 20일 확인" · "(2026-10-20 확인)" · "10.20 확인" (2026-10-20 사용자: 부자연스럽다)
# → 괄호 안 작은 회색 글씨 "(10.20 확인)". 인라인 style 이라 네이버·티스토리에 붙여도 남는다 (네이버 글자 크기 단계 13).
CHECK_DATE = re.compile(r"(?:\([ \t]*)?(?:(\d{4})[ \t]*(?:년|[.\-/])[ \t]*)?(\d{1,2})[ \t]*(?:월|[.\-/])[ \t]*(\d{1,2})[ \t]*일?"
                        r"[ \t]*확인(?![가-힣])(?:[ \t]*\))?")
CHECK_DATE_STYLE = "color:#999999;font-size:13px"


def soft_check_dates(body_html: str) -> str:
    """글자 부분(태그 밖)의 확인 날짜만 바꾼다. 해는 쓰지 않는다 (사용자가 든 꼴 '10.20')."""
    def one(m: re.Match) -> str:
        month, day = int(m.group(2)), int(m.group(3))
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return m.group(0)
        return f'<span style="{CHECK_DATE_STYLE}">({month}.{day} 확인)</span>'
    opened = f'<span style="{CHECK_DATE_STYLE}">'
    parts = re.split(r"(<[^>]+>)", body_html)
    out = []
    for i, part in enumerate(parts):  # 이미 바꾼 것(그 span 바로 안의 글)은 다시 감싸지 않는다
        done = part.startswith("<") or (i >= 2 and parts[i - 1] == opened)
        out.append(part if done else CHECK_DATE.sub(one, part))
    return "".join(out)


def plain_text(body_html: str, drop_slots: bool = False) -> str:
    """서식 없는 글. drop_slots 면 사진·그림 자리 상자는 뺀다 (글자 수 셀 때)."""
    if drop_slots:
        body_html = re.sub(r'<p[^>]*class="wr-slot"[^>]*>.*?</p>', "", body_html, flags=re.S)
    body_html = re.sub(r"<br\s*/?>\n?", "\n", body_html)
    body_html = re.sub(r"</t[hd]>\s*(?=<t[hd])", "\t", body_html)  # 표 한 줄은 탭으로 이어 붙인다
    body_html = re.sub(r"</(p|h\d|li|tr|blockquote)>", "\n", body_html)
    text = html.unescape(re.sub(r"<[^>]+>", "", body_html))
    return re.sub(r"\n{3,}", "\n\n", text).strip()



# 티스토리·블로거에 붙일 HTML (2026-10-22 사용자: 글 안 문단 위아래 간격이 답답하다 · 사진은 가운데 620).
# 스킨은 문단 margin 을 0 으로 두는 경우가 많아 문단이 붙는다 → 티스토리 편집기가 빈 줄에 쓰는 빈 문단을 맨 바깥 블록 사이에 끼운다.
# 사진은 가운데 줄에 폭 620 (작은 화면은 max-width 100% 로 줄어든다). 이미 빈 줄이 든 편집기 HTML 에는 끼우지 않는다.
TISTORY_GAP = '<p data-ke-size="size16">&nbsp;</p>'
_TOP_BLOCK = re.compile(r"<(p|h[2-4]|ul|ol|table|blockquote|hr|pre|figure)\b", re.I)
_EMPTY_P = re.compile(r"<p[^>]*>(?:\s|&nbsp;|\xa0|<br\s*/?>)*</p>")
IMG_WIDTH = 620
POSTER_WIDTH = 300  # 설명(alt)이 '포스터'로 시작하는 그림 (2026-10-23 사용자: 포스터는 작게 고정)
# 글 덩어리(## 소제목) 앞은 빈 줄 셋 — 엔터 두 번 더 (2026-10-22 사용자: 자주 묻는 것 · 화수 환산기 · 장별 대응 사이가 답답하다.
# 스킨이 아니라 글에 넣는다: 스킨은 모든 글에 걸린다). 네이버 붙여넣기도 같은 수 (naver_writing.render).
SECTION_GAPS = 3


class _TopBlocks(HTMLParser):
    """맨 바깥 블록이 시작하는 (줄, 칸, 태그)를 찾는다."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.depth, self.starts = 0, []

    def handle_starttag(self, tag, attrs):
        if self.depth == 0 and _TOP_BLOCK.match(f"<{tag}"):
            self.starts.append((*self.getpos(), tag))
        if tag not in ("br", "img", "hr"):
            self.depth += 1

    def handle_endtag(self, tag):
        if tag not in ("br", "img", "hr"):
            self.depth = max(0, self.depth - 1)


def tistory_html(body_html: str) -> str:
    """티스토리·블로거에 붙일 HTML (2026-10-22 사용자: 문단 사이가 답답하다 · 사진은 가운데 620).
    티스토리 본문은 문단 여백이 0 이라 맨 바깥 블록 사이에 빈 줄 하나, ## 소제목 앞에는 SECTION_GAPS 줄을 끼운다.
    소제목 바로 뒤에는 끼우지 않아 소제목이 아래 글에 붙는다. 이미 빈 줄이 있는 글(사용자가 편집기에서 띄운 글)은 그대로 둔다."""
    out = re.sub(r'<img (?![^>]*\bwidth=)(?=[^>]*\balt="포스터)', f'<img width="{POSTER_WIDTH}" ', body_html)  # 포스터는 300
    out = re.sub(r"<img (?![^>]*\bwidth=)", f'<img width="{IMG_WIDTH}" ', out)
    if _EMPTY_P.search(out):
        return out
    parser = _TopBlocks()
    parser.feed(out)
    parser.close()
    lines = out.split("\n")
    offsets = [0]
    for line in lines[:-1]:
        offsets.append(offsets[-1] + len(line) + 1)
    starts = parser.starts
    cuts = [(offsets[ln - 1] + col, SECTION_GAPS if tag == "h2" else 1)  # 첫 블록 앞에는 넣지 않는다
            for (ln, col, tag), (_, _, before) in zip(starts[1:], starts) if not re.fullmatch(r"h[2-4]", before)]
    for at, n in reversed(cuts):
        out = out[:at] + TISTORY_GAP * n + out[at:]
    return out
