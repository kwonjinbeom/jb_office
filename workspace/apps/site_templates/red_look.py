"""빨강 정갈 글 모양 (SiteCategory.look = "red") — black_lukey › 영화·OTT 공개 (2026-10-28 사용자).

지금 구조 그대로, 작품 제목은 막대 테마에 빨강만 입히고, 나머지는 눈잎 정갈(nunip_look)의 표·카드 디테일을 가져와 남색 자리를 빨강으로
(사용자: "눈잎 공모주·주택의 표나 테이블 디테일을 그대로 가져와 색만", "글자에 _ 붙이는 건 빼줘").
도안: 콘텐츠/블로그_카페/memorily_네이버/도안_영화OTT_빨강.html (왼쪽 예전 · 오른쪽 이 모양).
- 맨 위 인용 → '한눈에' 연회색 상자 (네이버는 인용을 따옴표 인용구로 바꾸므로 한 칸 표로)
- 보통 소제목(##) → 작은 빨간 번호(01) + 검정 굵은 제목, 아래 가는 회색 줄
- 작품 제목(work_titles 의 막대 표) → 막대만 빨강, 제목 글자 검정 굵게
- 표 → 연회색 머리 칸 · 빨간 머리 글자 · 2px 빨간 윗줄 · 몸은 가는 가로줄 · 숫자 칸 오른쪽 · 첫 칸 검정 굵게
- 정보 카드(::: 작품 …) → B 레드 라인: 흰 머리 줄에 빨간 윗줄·검정 아랫줄('작품 정보'만 빨강), 연회색 이름표 칸(검정 글자 · 이모지 그대로) · 세로 줄 · 맨 아래 검정 2px
- 굵게 → 빨강
네이버 붙여넣기 HTML(naver_writing.render.paste_html 결과)을 바꾼다 — 남는 꼴(글자색·바탕색·굵게·크기·표 칸 테두리)만 쓴다.
"""
import re

RED, INK, TINT, LINE = "#e50914", "#141414", "#f4f5f7", "#eeeeee"
FONT = "font-family:나눔바른고딕;line-height:1.8;margin:0"

BLOCKQUOTE = re.compile(r"<blockquote[^>]*>(.*?)</blockquote>", re.S)
H2 = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S)
PLAIN_TABLE = re.compile(r'<table style="border-collapse:collapse;width:100%;font-size:15px">.*?</table>', re.S)
CARD_TABLE = re.compile(r'<table style="border-collapse:collapse;width:100%;font-size:15px;margin:18px 0"><tbody>(.*?)</tbody></table>', re.S)
ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
CELL = re.compile(r'<td style="([^"]*)">(.*?)</td>', re.S)
NUMBERISH = re.compile(r"^[\d,.\s~·%분회부작약()+\-–]+$")
WORK_BAR = "border:1px solid #ffffff;background-color:#555555;width:5px;padding:0"


def _p(text, size, color, bold=False):
    return f'<p style="{FONT};font-size:{size}px;color:{color}' + (";font-weight:bold" if bold else "") + f'">{text}</p>'


def _td(inner, style, size=15):
    return f'<td style="{FONT};font-size:{size}px;{style}">{inner}</td>'


def _table(rows, margin="0"):
    return f'<table style="border-collapse:collapse;width:100%;margin:{margin}"><tbody>{rows}</tbody></table>'


def _lead(m):
    inner = re.sub(r"<p[^>]*>", f'<p style="{FONT};font-size:15px;color:#333333">', m.group(1).strip())
    return _table("<tr>" + _td(_p("한눈에", 13, RED, True) + inner, f"padding:20px 22px;border:1px solid {TINT};background-color:{TINT}") + "</tr>", "18px 0")


def _plain_table(m):
    rows = [CELL.findall(r) for r in ROW.findall(m.group(0))]
    if not rows:
        return m.group(0)
    body = rows[1:]
    cols = max(len(r) for r in rows)
    right = [i > 0 and bool(body) and all(i < len(r) and NUMBERISH.match(re.sub(r"<[^>]+>", "", r[i][1]).strip() or "x") for r in body)
             for i in range(cols)]
    out = []
    for k, row in enumerate(rows):
        cells = []
        for i, (style, text) in enumerate(row):
            align = "right" if right[i] else "left"
            if k == 0:
                width = ";width:15%" if i == 0 and len(row) >= 4 else ""  # 날짜 칸이 두 줄로 꺾이지 않게
                cells.append(_td(re.sub(r"</?strong>", "", text).strip(),
                                 f"padding:10px 12px;border:1px solid {TINT};border-top:2px solid {RED};background-color:{TINT};"
                                 f"color:{RED};font-weight:bold;text-align:{align}{width}"))
            else:
                hot = ";background-color:#fff4e5" if "#fff4e5" in style else ""
                first = f";color:{INK};font-weight:bold" if i == 0 else ""
                cells.append(_td(text.strip(), f"padding:10px 12px;border:1px solid #ffffff;border-bottom:1px solid {LINE};text-align:{align}{first}{hot}"))
        out.append("<tr>" + "".join(cells) + "</tr>")
    return f'<table style="border-collapse:collapse;width:100%;font-size:15px;margin:0"><tbody>{"".join(out)}</tbody></table>'


def _card(m):
    """정보 카드 — B 레드 라인 (2026-10-28 사용자가 예시안에서 고름: 이전 템플릿의 머리 줄 + 이름표 칸 짜임에 빨강·검정 선).
    머리 줄은 흰 바탕에 빨간 3px 윗줄 · 검정 아랫줄, '작품 정보'만 빨강 · 이름은 검정 굵게. 몸은 연회색 이름표 칸(검정 글자, 이모지 그대로) ·
    옅은 가로줄 · 이름표와 값 사이 세로 줄, 맨 아래 검정 2px."""
    cells = [text for _, text in CELL.findall(m.group(1))]
    if len(cells) < 2:
        return m.group(0)
    head = f"border:1px solid #ffffff;border-top:3px solid {RED};border-bottom:1px solid {INK};background-color:#ffffff;font-weight:bold"
    out = ("<tr>" + _td(cells[0].strip(), f"width:28%;padding:10px 12px;{head};color:{RED};text-align:center", 13)
           + _td(cells[1].strip(), f"padding:10px 14px;{head};color:{INK}", 16) + "</tr>")
    pairs = list(zip(cells[2::2], cells[3::2]))
    for n, (k, v) in enumerate(pairs):
        bottom = f"border-bottom:2px solid {INK}" if n == len(pairs) - 1 else f"border-bottom:1px solid {LINE}"
        out += ("<tr>" + _td(k.strip(), f"padding:9px 12px;border:1px solid #ffffff;{bottom};border-right:1px solid {LINE};"
                                        f"background-color:#fafafa;color:#333333;font-weight:bold")
                + _td(v.strip(), f"padding:9px 14px;border:1px solid #ffffff;{bottom};background-color:#ffffff;color:#333333") + "</tr>")
    return _table(out, "18px 0")


def red_html(rich):
    """네이버 붙여넣기 HTML → 빨강 정갈."""
    out = BLOCKQUOTE.sub(_lead, rich, count=1)
    n = [0]

    def h2(m):
        n[0] += 1
        head = (f'<span style="font-size:15px;color:{RED};font-weight:bold">{n[0]:02d}</span>&nbsp; '
                f'<span style="font-size:24px;color:{INK};font-weight:bold">{m.group(1).strip()}</span>')
        return _table("<tr>" + _td(head, f"padding:0 0 10px;border:1px solid #ffffff;border-bottom:1px solid {LINE}", 24) + "</tr>")

    out = H2.sub(h2, out)
    out = out.replace(WORK_BAR, f"border:1px solid {RED};background-color:{RED};width:5px;padding:0")  # 작품 제목 막대
    out = re.sub(r'(<p style="[^"]*font-size:19px;[^"]*)color:#555555', rf"\1color:{INK};font-weight:bold", out)
    out = PLAIN_TABLE.sub(_plain_table, out)
    out = CARD_TABLE.sub(_card, out)
    return re.sub(r"<strong>", f'<strong style="color:{RED}">', out)


PROMPT = """## 글 모양 — 빨강 정갈 (이 카테고리만 · 2026-10-28 사용자)
모양(빨간 포인트·연회색 상자·가는 줄·소제목 번호)은 붙여 넣는 HTML 이 그린다. 변환본은 아래처럼 '쓰기만' 한다 (HTML·색 코드는 넣지 않는다).
- 맨 위 인용(>)은 '한눈에' 연회색 상자가 된다: 2~3문장, 기준일(○월 ○일 ○○ 공지 기준)은 여기에.
- 보통 `## 소제목`(공개 달력 · 뭐부터 볼까 등)은 앞에 01·02 번호가 저절로 붙는다 — 번호·이모지를 쓰지 않는다.
- 작품은 지금처럼 `## 작품 이름 · 공개일` + 바로 아래 `::: 작품` 카드 — 빨간 막대가 붙은 작품 제목이 된다.
- 작품 카드는 '레드 라인' 표로 그려진다 (머리 줄 빨간 윗줄·검정 아랫줄, 연회색 이름표 칸, 맨 아래 검정 줄). 이름표는 `이모지 이름표 | 값` 그대로 — 이모지를 빼지 않는다. 이름표는 짧게 (종류·장르 · 공개 · 볼 곳 · 러닝타임/회차 · 관람 등급 · 감독 · 주요 출연 · 화제·수상 · 예고편).
- 표는 그대로 (머리 줄 연회색 바탕·빨간 글자, 숫자 칸 오른쪽). 굵게(**)는 빨강으로 보인다 — 한 단락에 한 번 이하."""
