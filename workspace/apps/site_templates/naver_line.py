"""네이버 '가는 선' 표 모양 (SiteCategory.look = line_green · line_orange) — black_lukey › 지역 놀거리 · 축제·행사 (2026-10-28 사용자).

예시안(콘텐츠/블로그_카페/memorily_네이버/예시안_지역놀거리_표.html)에서 사용자가 고른 조합: "일반 표는 1번 가는 선, 장소 카드는 4번 모노 초록 포인트,
축제·행사는 주황 포인트". 글의 다른 모양(소제목·인용·사진·지도)은 그대로 — 표 두 종류만 바꾼다.
- 일반 표: 세로줄 없이 위아래 굵은 검정 선 + 가는 가로줄, 머리 줄 검정 굵게, 첫 칸 굵게, 숫자 칸 오른쪽, '합계' 줄은 위아래 검정 선
- 정보 카드(::: 장소|맛집 …): 연회색 이름표 칸 · 회색 선, 머리 줄에만 포인트 색 윗줄 3px · 포인트 색 라벨 · 검정 굵은 이름
네이버 붙여넣기 HTML(naver_writing.render.paste_html 결과)을 바꾼다 — 남는 꼴(글자색·바탕색·굵게·크기·표 칸 테두리)만.
"""
import re

ACCENTS = {"line_green": "#1f6f5c", "line_orange": "#f0561d"}
INK, LINE, MONO, MONO_LINE = "#222222", "#e6e6e6", "#f6f6f6", "#e4e4e4"
FONT = "font-family:나눔바른고딕;line-height:1.8;margin:0"
PLAIN_TABLE = re.compile(r'<table style="border-collapse:collapse;width:100%;font-size:15px">.*?</table>', re.S)
CARD_TABLE = re.compile(r'<table style="border-collapse:collapse;width:100%;font-size:15px;margin:18px 0"><tbody>(.*?)</tbody></table>', re.S)
ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
CELL = re.compile(r'<td style="([^"]*)">(.*?)</td>', re.S)
NUMBERISH = re.compile(r"^[\d,.\s~·%원분회약()+\-–→:]+$")


def _td(inner, style, size=15):
    return f'<td style="{FONT};font-size:{size}px;{style}">{inner}</td>'


def _text(html):
    return re.sub(r"<[^>]+>", "", html).strip()


def _plain(m):
    rows = [CELL.findall(r) for r in ROW.findall(m.group(0))]
    if not rows:
        return m.group(0)
    body = rows[1:]
    cols = max(len(r) for r in rows)
    right = [i > 0 and bool(body) and all(i < len(r) and NUMBERISH.match(_text(r[i][1]) or "x") for r in body) for i in range(cols)]
    first_w = ";width:20%" if _text(rows[0][0][1]) == "시간" else ""  # 시각 칸이 꺾이지 않게
    out = "<tr>" + "".join(_td(re.sub(r"</?strong>", "", text).strip(),
                                f"padding:10px 12px;border:1px solid #ffffff;border-top:2px solid {INK};border-bottom:1px solid {INK};color:{INK};font-weight:bold"
                                + (";text-align:right" if right[i] else ";text-align:left") + (first_w if i == 0 else ""))
                           for i, (_, text) in enumerate(rows[0])) + "</tr>"
    for k, row in enumerate(body):
        total = k == len(body) - 1 and _text(row[0][1]) == "합계"
        cells = ""
        for i, (style, text) in enumerate(row):
            base = (f"padding:10px 12px;border:1px solid #ffffff;border-top:1px solid {INK};border-bottom:2px solid {INK};color:{INK};font-weight:bold" if total
                    else f"padding:10px 12px;border:1px solid #ffffff;border-bottom:1px solid {LINE}" + (f";color:{INK};font-weight:bold" if i == 0 else ""))
            hot = ";background-color:#fff4e5" if "#fff4e5" in style else ""
            cells += _td(text.strip(), base + hot + (";text-align:right" if right[i] else ";text-align:left"))
        out += f"<tr>{cells}</tr>"
    return f'<table style="border-collapse:collapse;width:100%;font-size:15px;margin:0"><tbody>{out}</tbody></table>'


def _card(m, accent):
    cells = [text for _, text in CELL.findall(m.group(1))]
    if len(cells) < 2:
        return m.group(0)
    out = ("<tr>" + _td(cells[0].strip(), f"width:28%;padding:10px 12px;border:1px solid {MONO_LINE};border-top:3px solid {accent};background-color:#ffffff;"
                                         f"color:{accent};font-weight:bold;text-align:center", 13)
           + _td(cells[1].strip(), f"padding:10px 14px;border:1px solid {MONO_LINE};border-top:3px solid {accent};background-color:#ffffff;color:{INK};font-weight:bold", 16)
           + "</tr>")
    out += "".join("<tr>" + _td(k.strip(), f"padding:9px 12px;border:1px solid {MONO_LINE};background-color:{MONO};color:#444444;font-weight:bold")
                   + _td(v.strip(), f"padding:9px 14px;border:1px solid {MONO_LINE};background-color:#ffffff;color:#333333") + "</tr>"
                   for k, v in zip(cells[2::2], cells[3::2]))
    return f'<table style="border-collapse:collapse;width:100%;font-size:15px;margin:18px 0"><tbody>{out}</tbody></table>'


def line_html(rich, look):
    """네이버 붙여넣기 HTML → 일반 표 '가는 선' + 정보 카드 '모노 + 포인트 색'."""
    accent = ACCENTS[look]
    out = PLAIN_TABLE.sub(_plain, rich)
    return CARD_TABLE.sub(lambda m: _card(m, accent), out)
