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
QUOTE_STYLE = "margin:18px 0;padding:12px 16px;border-left:4px solid #d1d5db;background:#f9fafb;color:#374151"
HR_STYLE = "border:0;border-top:1px solid #e5e7eb;margin:28px 0"
IMG_STYLE = "max-width:100%;height:auto"

LINE_MARK = re.compile(r"^\s*(?:>\s*)?(?:\[(사진|그림|캡션)\]|(📷|🖼️?))\s*[:：]?\s*(.*)$")


def _mark_lines(text: str) -> str:
    """[사진]·[그림]·[캡션] 줄을 인라인 style 을 단 HTML 문단으로 바꾼다. 마크다운은 이 줄을 건드리지 않는다."""
    out = []
    for line in text.split("\n"):
        m = LINE_MARK.match(line)
        if not m:
            out.append(line)
            continue
        kind = m.group(1) or ("사진" if m.group(2) == "📷" else "그림")
        body = html.escape(m.group(3).strip())
        if kind == "캡션":
            block = f'<p style="{CAPTION_STYLE}">{body}</p>'
        elif kind == "사진":
            block = f'<p class="wr-slot" style="{SLOT_STYLE["photo"]}">📷 {body or "여기에 내 사진 올리기"}</p>'
        else:
            block = f'<p class="wr-slot" style="{SLOT_STYLE["figure"]}">🖼 여기에 그림 올리기{": <strong>" + body + "</strong>" if body else ""}</p>'
        out.extend(["", block, ""])
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
    cells = {f"{b};text-align:{a}" for b in (CELL_STYLE, HEAD_STYLE) for a in ("left", "center", "right")}
    return {s.replace(" ", "") for s in base | cells | {CELL_STYLE, HEAD_STYLE}}


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
    out = _flatten_header(out)
    out = out.replace("<blockquote>", f'<blockquote style="{QUOTE_STYLE}">')
    out = re.sub(r"<hr\s*/?>", f'<hr style="{HR_STYLE}">', out)
    out = IMAGE_BLOCK.sub(_image, out)
    return out


def render_body(text: str) -> str:
    """본문 → 블로그에 붙여넣을 HTML. 편집기 HTML 이면 걸러 내고, 마크다운이면 변환한다."""
    if is_html(text):
        return _decorate(clean_html(text))
    text = re.sub(r"<!--.*?-->", "", (text or "").replace("\r\n", "\n"), flags=re.S)
    out = _decorate(markdown.markdown(_mark_lines(text), extensions=["tables", "sane_lists", "nl2br"]))
    return clean_html(out)  # 마크다운 안에 섞인 날 HTML 도 같은 기준으로 거른다


def plain_text(body_html: str, drop_slots: bool = False) -> str:
    """서식 없는 글. drop_slots 면 사진·그림 자리 상자는 뺀다 (글자 수 셀 때)."""
    if drop_slots:
        body_html = re.sub(r'<p[^>]*class="wr-slot"[^>]*>.*?</p>', "", body_html, flags=re.S)
    body_html = re.sub(r"<br\s*/?>\n?", "\n", body_html)
    body_html = re.sub(r"</t[hd]>\s*(?=<t[hd])", "\t", body_html)  # 표 한 줄은 탭으로 이어 붙인다
    body_html = re.sub(r"</(p|h\d|li|tr|blockquote)>", "\n", body_html)
    text = html.unescape(re.sub(r"<[^>]+>", "", body_html))
    return re.sub(r"\n{3,}", "\n\n", text).strip()
