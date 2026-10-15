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
            block = f'<p class="wr-slot" style="{SLOT_STYLE["figure"]}">🖼 여기에 그림 올리기{": <b>" + body + "</b>" if body else ""}</p>'
        out.extend(["", block, ""])
    return "\n".join(out)


def _cell(tag: str, align: str | None) -> str:
    base = HEAD_STYLE if tag == "th" else CELL_STYLE
    return f'<{tag} style="{base};text-align:{align or "left"}">'


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
        out = f'<p class="wr-slot" style="{SLOT_STYLE["figure"]}">🖼 여기에 그림 올리기: <b>{name}</b></p>'
    if caption:
        out += f'\n<p style="{CAPTION_STYLE}">{caption}</p>'
    return out


def render_body(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", (text or "").replace("\r\n", "\n"), flags=re.S)
    out = markdown.markdown(_mark_lines(text), extensions=["tables", "sane_lists", "nl2br"])
    out = out.replace("<table>", f'<table style="{TABLE_STYLE}">')
    out = re.sub(r'<(th|td)(?: style="text-align: (\w+);")?>', lambda m: _cell(m.group(1), m.group(2)), out)
    out = out.replace("<blockquote>", f'<blockquote style="{QUOTE_STYLE}">')
    out = re.sub(r"<hr\s*/?>", f'<hr style="{HR_STYLE}">', out)
    out = IMAGE_BLOCK.sub(_image, out)
    return out


def plain_text(body_html: str, drop_slots: bool = False) -> str:
    """서식 없는 글. drop_slots 면 사진·그림 자리 상자는 뺀다 (글자 수 셀 때)."""
    if drop_slots:
        body_html = re.sub(r'<p class="wr-slot"[^>]*>.*?</p>', "", body_html, flags=re.S)
    body_html = re.sub(r"<br\s*/?>\n?", "\n", body_html)
    body_html = re.sub(r"</t[hd]>\s*(?=<t[hd])", "\t", body_html)  # 표 한 줄은 탭으로 이어 붙인다
    body_html = re.sub(r"</(p|h\d|li|tr|blockquote)>", "\n", body_html)
    text = html.unescape(re.sub(r"<[^>]+>", "", body_html))
    return re.sub(r"\n{3,}", "\n\n", text).strip()
