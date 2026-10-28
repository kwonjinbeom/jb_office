"""눈잎 정갈 글 모양 (SiteCategory.look = "nunip") — 청년·신혼 정책 · 주택 공고 · 공모주 · 생활 (2026-10-28 사용자).

미리캔버스 '파랑과 회색의 기본적인 강연 발표자료'의 느낌만 블로그 글에 녹인다 (같은 날 첫 도안은 "PPT 를 옮겨 놓은 것 같다, 과하다").
도안: 콘텐츠/블로그_카페/눈잎_티스토리/도안_생활정책_남색회색.html — 사용자가 "좋다, 앞으로 적용".
- 남색 #3b598d 한 가지는 포인트만: 소제목 앞 작은 번호 · 소제목 끝 '_' · 굵게 · 표 머리 글자와 윗줄 · 이름표.
- 연회색 #f4f5f7 바탕은 맨 위 '한눈에_' 상자와 표 머리 칸만. 나머지는 가는 회색 줄과 여백.
- 소제목 바로 아래 기울임 한 줄(*…*)은 회색 설명 줄. 목록이 모두 '**이름표** 값' 이면 이름표 줄 목록.
글꼴·줄 간격은 눈잎 스킨(Odyssey + 눈잎 디자인 CSS)이 정한다 — 붙여 넣는 HTML 에는 글꼴을 넣지 않는다.
티스토리는 붙여 넣은 HTML 의 class 를 믿을 수 없어 모양은 전부 인라인 style (유디 메모지 looks.py 와 같은 방식).
"""
import re

NAVY, TINT, LINE, GRAY = "#3b598d", "#f4f5f7", "#eeeeee", "#9ca3af"
S = {
    "wrap": "color:#333333;word-break:keep-all",
    "p": "margin:0 0 16px",
    "lead": f"background-color:{TINT};border-radius:6px;padding:20px 22px;margin:0 0 34px",
    "lead_label": f"margin:0 0 8px;font-size:13px;font-weight:700;color:{NAVY};letter-spacing:.3px",
    "lead_p": "margin:0;font-size:15px",
    "quote": f"background-color:{TINT};border-radius:6px;padding:16px 20px;margin:0 0 24px",
    "h2": "margin:44px 0 0;padding:0;border:0;font-size:21px;line-height:1.45;font-weight:800;color:#222222",
    "h2_alone": f"margin:44px 0 20px;padding:0 0 12px;border:0;border-bottom:1px solid {LINE};font-size:21px;line-height:1.45;font-weight:800;color:#222222",
    "num": f"font-size:14px;color:{NAVY};margin-right:8px",
    "cursor": f"color:{NAVY}",
    "sub": f"margin:4px 0 20px;padding-bottom:12px;border-bottom:1px solid {LINE};font-size:14px;color:{GRAY}",
    "h3": f"margin:24px 0 6px;padding:0;border:0;font-size:16px;font-weight:700;color:{NAVY}",
    "strong": f"font-weight:700;color:{NAVY}",
    "table": "width:100%;border-collapse:collapse;font-size:15px;margin:0 0 20px",
    "th": f"background-color:{TINT};color:{NAVY};padding:10px 14px;font-weight:700;border:0;border-top:2px solid {NAVY};vertical-align:top",
    "td": f"padding:10px 14px;border:0;border-bottom:1px solid {LINE};vertical-align:top",
    "hot": "background-color:#fff4e5",
    "row": f"margin:0;padding:9px 0;border-bottom:1px solid {LINE}",
    "row_last": f"margin:0 0 24px;padding:9px 0;border-bottom:1px solid {LINE}",
    "label": f"display:inline-block;min-width:110px;font-weight:700;color:{NAVY}",
    "card_name": "margin:24px 0 6px;font-size:16px;font-weight:700;color:#222222",
    "ul": "margin:0 0 20px;padding-left:20px",
    "li": "margin:0 0 8px",
    "hr": f"border:0;border-top:1px solid {LINE};margin:36px 0",
    "source": f"margin:40px 0 0;padding-top:14px;border-top:1px solid {LINE};font-size:13px;color:{GRAY}",
    "caption": f"text-align:center;color:{GRAY};font-size:13px;margin:6px 0 24px",
}

GAP = '<p data-ke-size="size16">&nbsp;</p>'
QUOTE = re.compile(r"<blockquote[^>]*>(.*?)</blockquote>", re.S)
H2 = re.compile(r"<h2[^>]*>(.*?)</h2>\s*(<p><em>((?:(?!</em>).)*)</em></p>)?", re.S)
CARD = re.compile(r'<table style="border-collapse:collapse;width:100%;font-size:15px;margin:18px 0"><tbody>(.*?)</tbody></table>', re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
TABLE = re.compile(r"<table\b[^>]*>(.*?)</table>", re.S)
ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
TCELL = re.compile(r"<t([hd])([^>]*)>(.*?)</t[hd]>", re.S)
UL = re.compile(r"<ul>(.*?)</ul>", re.S)
LI = re.compile(r"<li>(.*?)</li>", re.S)
LABEL_LI = re.compile(r"^\s*<strong>([^<]{1,14})</strong>\s*[:：·-]?\s*(.+)$", re.S)
NUMBERISH = re.compile(r"^[\d,.\s~·%원만억천약()+\-–]+$")
CAPTION = re.compile(r'<p style="text-align:center;color:#6b7280;font-size:14px;margin-top:-8px">(.*?)</p>', re.S)


def _lead(m, first):
    inner = re.sub(r"<p[^>]*>", f'<p style="{S["lead_p"]}">', m.group(1).strip())
    if not first:
        return f'<div style="{S["quote"]}">{inner}</div>'
    return f'<div style="{S["lead"]}"><p style="{S["lead_label"]}">한눈에_</p>{inner}</div>'


def _card(m):
    """정보 카드(::: 종류 | 이름) → 이름 한 줄 + 이름표 줄 목록 (색 칸 표 대신)"""
    cells = CELL.findall(m.group(1))
    if len(cells) < 2:
        return m.group(0)
    pairs = list(zip(cells[2::2], cells[3::2]))
    rows = [f'<p style="{S["row_last"] if i == len(pairs) - 1 else S["row"]}"><span style="{S["label"]}">{k.strip()}</span>{v.strip()}</p>'
            for i, (k, v) in enumerate(pairs)]
    return f'<p style="{S["card_name"]}">{cells[1].strip()}</p>' + "".join(rows)


def _table(m):
    rows = [TCELL.findall(r) for r in ROW.findall(m.group(1))]
    if not rows:
        return m.group(0)
    body = rows[1:]
    cols = max(len(r) for r in rows)
    right = [i > 0 and bool(body) and all(i < len(r) and NUMBERISH.match(re.sub(r"<[^>]+>", "", r[i][2]).strip() or "x") for r in body)
             for i in range(cols)]  # 첫 칸은 줄 이름이라 늘 왼쪽
    out = []
    for n, row in enumerate(rows):
        cells = []
        for i, (_, attrs, text) in enumerate(row):
            align = "right" if right[i] else "left"
            if n == 0:
                text = re.sub(r"</?strong>", "", text).strip()
                cells.append(f'<th style="{S["th"]};text-align:{align}">{text}</th>')
            else:
                hot = ";" + S["hot"] if "#fff4e5" in attrs else ""
                cells.append(f'<td style="{S["td"]};text-align:{align}{hot}">{text.strip()}</td>')
        out.append("<tr>" + "".join(cells) + "</tr>")
    return f'<table style="{S["table"]}"><tbody>{"".join(out)}</tbody></table>'


def _list(m):
    items = [re.sub(r"^\s*<p>|</p>\s*$", "", i.strip()) for i in LI.findall(m.group(1))]  # 빈 줄로 띄운 목록은 <li><p>…</p></li>
    labels = [LABEL_LI.match(i) for i in items]
    if items and all(labels) and all(not l.group(1).strip().endswith((".", "?", "!")) for l in labels):
        return "".join(f'<p style="{S["row_last"] if n == len(labels) - 1 else S["row"]}"><span style="{S["label"]}">'
                       f'{l.group(1).strip()}</span>{l.group(2).strip()}</p>' for n, l in enumerate(labels))
    return f'<ul style="{S["ul"]}">' + "".join(f'<li style="{S["li"]}">{i}</li>' for i in items) + "</ul>"


def nunip_html(body_html):
    """티스토리용 HTML(tistory_html 결과) → 눈잎 정갈 모양. 빈 줄 문단은 빼고 간격은 각 블록의 margin 이 맡는다."""
    out = body_html.replace(GAP, "")
    out = CARD.sub(_card, out)
    out = TABLE.sub(_table, out)
    lead = [out.lstrip().startswith("<blockquote")]  # 글 맨 위 인용만 '한눈에_' 상자

    def quote(m):
        first, lead[0] = lead[0], False
        return _lead(m, first)

    out = QUOTE.sub(quote, out)
    n = [0]

    def h2(m):
        n[0] += 1
        text = m.group(1).strip()
        num = re.match(r"^(\d{1,2})[.)]\s*", text)
        if num:
            text = text[num.end():]
        label = f"{int(num.group(1)) if num else n[0]:02d}"
        head = f'<span style="{S["num"]}">{label}</span>{text}<span style="{S["cursor"]}">_</span>'
        if m.group(2):
            return f'<h2 style="{S["h2"]}">{head}</h2><p style="{S["sub"]}">{m.group(3).strip()}</p>'
        return f'<h2 style="{S["h2_alone"]}">{head}</h2>'

    out = H2.sub(h2, out)
    out = re.sub(r"<h3[^>]*>", f'<h3 style="{S["h3"]}">', out)
    out = UL.sub(_list, out)
    out = re.sub(r"<hr[^>]*>", f'<hr style="{S["hr"]}">', out)
    out = out.replace('<p style="color:#999999;font-size:13px">', f'<p style="{S["source"]}">')
    out = CAPTION.sub(lambda m: f'<p style="{S["caption"]}">{m.group(1)}</p>', out)
    out = re.sub(r"<p>", f'<p style="{S["p"]}">', out)
    out = re.sub(r"<strong>", f'<strong style="{S["strong"]}">', out)
    return f'<div style="{S["wrap"]}">\n{out}\n</div>'


PROMPT = """## 글 모양 — 눈잎 정갈 (남색·회색, 이 카테고리만 · 2026-10-28 사용자)
모양(남색 포인트·연회색 상자·가는 줄·소제목 번호)은 붙여 넣는 HTML 이 그린다. 변환본은 아래처럼 '쓰기만' 한다 (HTML·색 코드는 넣지 않는다).
- 맨 위 인용(>)은 '한눈에_' 상자가 된다: 2~3문장, 무엇이 · 언제까지 · 누구에게. 기준일(○월 ○일 ○○ 발표·공고 기준)은 여기에.
- `## 소제목` 은 앞에 01·02 번호, 끝에 '_' 가 저절로 붙는다 — 소제목에 번호·이모지를 쓰지 않는다. 짧은 말로 (예: `## 우리 집도 받나`, `## 얼마 받나`).
- 소제목 바로 다음 줄에 `*한 줄 설명*` (기울임 한 줄, 20자 안팎)을 두면 회색 설명 줄이 된다. 그 소제목의 답을 한 줄로 (예: `*두 줄 다 해당하면 신청 대상이에요*`). 없어도 되지만 소제목마다 두는 게 기본이다.
- 표는 그대로 (머리 줄은 연회색 바탕·남색 글자, 금액·숫자 칸은 오른쪽 정렬). 꼭 짚을 칸만 **굵게** — 남색으로 보인다.
- 일정·조건처럼 '이름표 + 값' 줄이 이어지면 목록으로 `- **신청** 2026년 6월 15일 ~ 12월 31일` (이름표는 짧게, 마침표 없이) — 가는 줄로 나뉜 이름표 줄이 된다. 문장으로 된 목록은 보통 목록.
- 굵게는 한 단락에 한 번 이하. 이모지·형광펜·색 글자는 쓰지 않는다.
- 맨 끝 `참고:` 줄은 가는 윗줄 아래 작은 회색 글자가 된다."""
