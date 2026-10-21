"""네이버 원고의 안전한 HTML 저장·마크다운 변환·서식 복사.

티스토리 구현을 바탕으로 별도 분리했다. 네이버용 서체·글자 크기·색·줄간격을 보존한다.
사진/그림 자리와 표 변환은 기존 티스토리와 같은 규칙을 쓴다.
붙여넣을 HTML에는 별도로 글자 크기와 네이버가 인식하는 글꼴 이름을 명시한다.
"""
import html
import re
from html.parser import HTMLParser

import markdown

from apps.writing.render import fix_bold, soft_check_dates

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
                "table", "thead", "tbody", "tr", "th", "td", "hr", "a", "img", "code", "span", "sup", "sub", "pre"}
RENAME_TAGS = {"b": "strong", "i": "em", "strike": "s", "del": "s", "h1": "h2", "h5": "h4", "h6": "h4", "div": "p"}
BLOCK_TAGS = {"p", "h2", "h3", "h4", "ul", "ol", "table", "blockquote", "hr"}
DROP_WITH_CONTENT = {"script", "style", "iframe", "object", "embed", "head", "title", "noscript", "template", "svg"}
VOID_TAGS = {"br", "hr", "img"}
STYLED_TAGS = ALLOWED_TAGS - {"br"}
ALIGN_STYLE = re.compile(r"^\s*text-align:\s*(left|center|right|justify)\s*;?\s*$")


def _known_styles() -> set[str]:
    """이 도구가 직접 다는 style 만 남긴다. 웹 문서에서 붙여 온 글꼴·색 같은 꾸밈은 버린다."""
    base = {*SLOT_STYLE.values(), CAPTION_STYLE, TABLE_STYLE, QUOTE_STYLE, HR_STYLE, IMG_STYLE,
            "text-align:center;margin:18px 0"}
    cells = {f"{b};text-align:{a}" for b in (CELL_STYLE, HEAD_STYLE) for a in ("left", "center", "right")}
    return {s.replace(" ", "") for s in base | cells | {CELL_STYLE, HEAD_STYLE}}


KNOWN_STYLES = _known_styles()


FONTS = {"나눔고딕": "Nanum Gothic", "나눔명조": "Nanum Myeongjo", "나눔바른고딕": "Nanum Barun Gothic",
         "나눔스퀘어": "Nanum Square", "마루부리": "MaruBuri"}
QUOTE_STYLES = [
    "margin:30px 0;padding:20px 24px;text-align:center;font-size:19px;line-height:1.8;border:0;color:#555555",
    "margin:30px 0;padding:4px 20px;border-left:3px solid #515151;color:#555555",
    "margin:30px 0;padding:22px;border:1px solid #b2b2b2;text-align:center;color:#555555",
    "margin:30px 0;padding:20px;border-top:2px solid #888888;border-bottom:2px solid #888888;text-align:center;color:#555555",
    "margin:30px 0;padding:22px;background-color:#f7f7f7;border:1px solid #dddddd;text-align:center;color:#555555",
    "margin:30px 0;padding:22px;border-left:2px solid #888888;border-right:2px solid #888888;text-align:center;color:#555555",
]
HR_STYLES = [
    f"border:0;border-top:{width}px {kind} {color};margin:30px auto;width:{size}"
    for width, kind, color, size in [(1,"solid","#dddddd","100%"),(1,"solid","#999999","30%"),
        (2,"solid","#555555","10%"),(1,"dashed","#aaaaaa","100%"),(2,"dotted","#aaaaaa","100%"),
        (3,"double","#aaaaaa","100%"),(3,"solid","#dddddd","100%"),(1,"solid","#555555","60%")]
]
KNOWN_STYLES |= {s.replace(" ", "") for s in QUOTE_STYLES + HR_STYLES}


def safe_style(value: str) -> str:
    """Preserve editor typography, never CSS URLs, arbitrary positioning or executable values."""
    if value.replace(" ", "").rstrip(";") in KNOWN_STYLES:
        return value
    kept = []
    for item in value.split(";"):
        name, sep, val = item.partition(":")
        name, val = name.strip().lower(), val.strip()
        ok = False
        if name == "font-family":
            ok = val.strip("\"'") in {*FONTS.values(), *FONTS.keys(), "Arial", "sans-serif", "serif", "monospace"}
        elif name == "font-size":
            ok = bool(re.fullmatch(r"(?:11|13|15|16|19|24|28|30|32|34|38|40)px", val))
        elif name in {"color", "background-color"}:
            ok = bool(re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?|transparent|rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)", val))
        elif name == "line-height":
            ok = bool(re.fullmatch(r"[12](?:\.\d{1,2})?|(?:1[5-9]0|2[01]0)%", val))
        elif name == "text-align":
            ok = val in {"left", "center", "right", "justify"}
        elif name == "font-weight":
            ok = val in {"normal", "bold", "400", "700"}
        elif name == "font-style":
            ok = val in {"normal", "italic"}
        elif name == "text-decoration":
            ok = val in {"none", "underline", "line-through", "underline line-through"}
        if sep and ok:
            kept.append(f"{name}:{val}")
    return ";".join(kept)


SAFE_URL = re.compile(r"^(https?://|mailto:|#|/(?!/))", re.I)


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
            if name == "style" and tag in STYLED_TAGS:
                cleaned = safe_style(value)
                if cleaned:
                    kept.append((name, cleaned))
            elif name == "class" and tag == "p" and value == "wr-slot":
                kept.append((name, value))
            elif name == "href" and tag == "a" and SAFE_URL.match(value.strip()):
                kept.append((name, value.strip()))
            elif name == "src" and tag == "img" and (re.match(r"^https?://", value.strip()) or
                    (len(value) <= 1400000 and re.fullmatch(r"data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/=]+", value))):
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
            if not data.strip() and (not self.stack or self.stack[-1] in {"table", "thead", "tbody", "tr"}):
                return
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
    if is_html(text):  # 편집기 글·HTML 로 저장한 변환본도 확인 날짜는 같게
        return soft_check_dates(_decorate(clean_html(text)))
    text = re.sub(r"<!--.*?-->", "", (text or "").replace("\r\n", "\n"), flags=re.S)
    out = _decorate(markdown.markdown(fix_bold(_mark_lines(text)), extensions=["tables", "sane_lists", "nl2br"]))
    return soft_check_dates(clean_html(out))  # 마크다운 안에 섞인 날 HTML 도 같은 기준으로 거른다


GAP = '<p style="font-family:나눔고딕;font-size:15px;line-height:1.8;margin:0">&nbsp;</p>'  # 네이버 빈 줄 한 칸 (본문 한 줄 높이)
BLOCKS = {"p", "h2", "h3", "h4", "ul", "ol", "table", "blockquote", "hr", "pre", "div"}
VOID = {"br", "img", "hr"}


class _PasteStyles(HTMLParser):
    """Clipboard HTML needs explicit typography: Naver cannot see our stylesheet.
    gaps: 맨 바깥 블록(문단·소제목·표·목록·인용) 사이에 빈 문단을 끼운다. 스마트에디터는 margin 을 버려서
    서버 화면(문단 아래 여백)과 달리 문단이 붙는다 (2026-10-20 사용자, 포스팅자동화/13 문서 '문단 사이 여백')."""
    def __init__(self, gaps=False):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.gaps = gaps
        self.depth = 0
        self.seen_block = False

    def handle_starttag(self, tag, attrs):
        if self.depth == 0 and tag in BLOCKS:
            if self.gaps and self.seen_block:
                self.out.append(GAP)
            self.seen_block = True
        if tag not in VOID:
            self.depth += 1
        attrs = dict(attrs)
        styles = {}
        if tag in {"p", "h2", "h3", "h4", "li", "td", "th"}:
            styles = {"font-family": "나눔고딕", "font-size": "15px", "line-height": "1.8", "margin": "0"}
        if tag in {"h2", "h3", "h4"}:
            styles.update({"font-size": {"h2": "24px", "h3": "19px", "h4": "16px"}[tag], "font-weight": "bold", "margin": "24px 0 16px"})
        for item in attrs.get("style", "").split(";"):
            name, sep, value = item.partition(":")
            if sep:
                styles[name.strip()] = value.strip()
        family = styles.get("font-family", "").strip("\"'")
        for label, font in FONTS.items():
            if family == font:
                styles["font-family"] = label
        if styles:
            attrs["style"] = ";".join(f"{key}:{value}" for key, value in styles.items())
        self.out.append("<" + tag + "".join(f' {key}="{html.escape(value or "", quote=True)}"' for key, value in attrs.items()) + ">")

    def handle_endtag(self, tag):
        if tag not in VOID:
            self.depth = max(0, self.depth - 1)
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        self.out.append(html.escape(data, quote=False))


def paste_html(body_html: str, gaps: bool = False) -> str:
    """네이버에 서식 그대로 붙일 HTML. gaps 는 마크다운으로 쓴 글(빈 줄로 문단을 나눈 글)일 때:
    문단 사이에 빈 줄을 넣어 서버 화면과 같은 간격으로. 네이버 편집기에서 쓴 글은 빈 줄이 이미 문단으로 들어 있다."""
    parser = _PasteStyles(gaps=gaps)
    parser.feed(clean_html(body_html))
    parser.close()
    return "".join(parser.out)


EMPTY_P = re.compile(r"<p[^>]*>(?:\s|&nbsp;|\xa0|<br\s*/?>)*</p>")


def needs_gaps(text: str, body_html: str) -> bool:
    """문단 사이 빈 줄을 넣을지: 마크다운 글, 또는 빈 문단이 하나도 없는 HTML (HTML 로 저장한 변환본).
    네이버 편집기에서 쓴 글은 빈 줄이 빈 문단으로 이미 들어 있다."""
    return not is_html(text) or not EMPTY_P.search(body_html)


def tag_line(tags: str) -> str:
    """네이버 태그 칸에 붙일 꼴: '#태그 #태그'. 쉼표로 붙여 넣으면 한 태그로 붙는다 (2026-10-20 사용자).
    네이버 태그에는 띄어쓰기가 안 들어가므로 태그 안의 빈칸은 뺀다."""
    items = [re.sub(r"\s+", "", t.strip().lstrip("#")) for t in re.split(r"[,\n]|(?<=\S)\s+(?=#)", tags or "")]
    return " ".join(f"#{t}" for t in items if t)


def plain_text(body_html: str, drop_slots: bool = False) -> str:
    """서식 없는 글. drop_slots 면 사진·그림 자리 상자는 뺀다 (글자 수 셀 때)."""
    if drop_slots:
        body_html = re.sub(r'<p[^>]*class="wr-slot"[^>]*>.*?</p>', "", body_html, flags=re.S)
    body_html = re.sub(r"<br\s*/?>\n?", "\n", body_html)
    body_html = re.sub(r"</t[hd]>\s*(?=<t[hd])", "\t", body_html)  # 표 한 줄은 탭으로 이어 붙인다
    body_html = re.sub(r"</(p|h\d|li|tr|blockquote)>", "\n", body_html)
    text = html.unescape(re.sub(r"<[^>]+>", "", body_html))
    return re.sub(r"\n{3,}", "\n\n", text).strip()
