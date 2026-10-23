"""카테고리 글 모양 (SiteCategory.look) — 내용이 아니라 화면 모양 (2026-10-23 사용자).

yudi — 눈잎 › 일본 여행. 사용자가 좋아하는 '유디' 블로그(m.blog.naver.com/hmjcpj)의 화면 짜임 (2026-10-23 화면을 열어 잰 값):
가운데 정렬(문단의 97%) · 한 줄에 한 호흡 · 나눔스퀘어 16px, 굵은 글씨 없음 · 강조는 청록 글자(#009D91)와 연두 형광펜(#E3FDC8) ·
소제목은 회색 큰따옴표 + 나눔명조 20px + 가는 회색 밑줄 · 큰 단락 사이 가운데 사선 · 정보는 모서리 접힌 메모지 상자(청록 글자) ·
목차는 가운데 좁은 표(머리 칸 연두) · 사진은 2장씩 붙인 콜라주 · 사진 설명은 작은 회색.

티스토리는 붙여 넣은 HTML 의 class 를 믿을 수 없어서 모양은 전부 인라인 style 로 넣는다 (스킨을 안 고쳐도 같은 모양).
글꼴만 스킨에 불러 둔다: 콘텐츠/블로그_카페/눈잎_티스토리/일본여행_글모양.css (없으면 기본 고딕·명조로 보인다).
"""
import re

LOOKS = {"yudi": "유디 메모지 (가운데 정렬·메모지 상자·명조 소제목)"}

FONT = "'NanumSquare','Nanum Square','나눔스퀘어',sans-serif"
SERIF = "'Nanum Myeongjo','나눔명조',serif"
TEAL, LIME, GRAY = "#009d91", "#e3fdc8", "#9b9b9b"
S = {
    "wrap": f"font-family:{FONT};font-size:16px;color:#111111;word-break:keep-all",
    "p": "text-align:center;line-height:2;margin:0 0 26px",
    "quote": f"font-family:Georgia,serif;font-size:44px;line-height:1;color:{GRAY};text-align:left;margin:64px 0 0",
    "h2": f"font-family:{SERIF};font-weight:400;font-size:21px;line-height:1.5;color:#111111;text-align:left;"
          f"border-bottom:1px solid {GRAY};padding:4px 0 12px;margin:4px 0 34px",
    "h3": f"font-family:{SERIF};font-weight:400;font-size:18px;color:#111111;text-align:center;margin:42px 0 18px",
    "cut": f"text-align:center;color:{GRAY};font-size:26px;line-height:1;margin:54px 0",
    "lead": "width:76%;margin:0 auto 44px;border-top:1px solid #555555;border-bottom:1px solid #555555;padding:16px 0;"
            "text-align:center;color:#555555;font-size:15px;line-height:1.9",
    "lead_p": "margin:0;text-align:center",
    "memo": "position:relative;max-width:560px;margin:34px auto;border:4px solid #d9d9d9;padding:30px 22px;text-align:center",
    "fold": "position:absolute;right:-4px;bottom:-4px;width:38px;height:38px;"
            "background:linear-gradient(315deg,#ffffff 50%,#c9c9c9 50%)",
    "memo_name": "margin:0 0 10px;color:#222222;font-size:16px;text-align:center",
    "memo_line": f"margin:0;color:{TEAL};font-size:15px;line-height:2;text-align:center",
    "table": "margin:30px auto;border-collapse:collapse;min-width:58%;font-size:15px",
    "th": f"border:1px solid #d5d5d5;background-color:{LIME};padding:11px 16px;text-align:center;font-weight:400",
    "td": "border:1px solid #d5d5d5;padding:11px 16px;text-align:center",
    "strong": f"font-weight:400;color:{TEAL}",
    "mark": f"background-color:{LIME}",
    "photos": "width:100%;border-collapse:collapse;margin:26px 0",
    "photo_td": "padding:2px;vertical-align:top",
    "photo_img": "display:block;width:100%;height:auto",
    "caption": "text-align:center;color:#999999;font-size:13px;margin:6px 0 26px",
    "a": f"color:{TEAL}",
}

MARK = re.compile(r"==(?=\S)([^=\n]+?)(?<=\S)==")


def yudi_source(text):
    """마크다운 변환 전: ==형광펜== → <u> (렌더가 거르지 않는 태그. 변환 뒤 형광펜으로 바꾼다)."""
    return MARK.sub(r"<u>\1</u>", text or "")


GAP = '<p data-ke-size="size16">&nbsp;</p>'
CARD = re.compile(r'<table style="border-collapse:collapse;width:100%;font-size:15px;margin:18px 0"><tbody>(.*?)</tbody></table>', re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
IMG_P = r'<p style="text-align:center;margin:18px 0">(<img [^>]*>)</p>'
CAP_P = r'<p style="text-align:center;color:#6b7280;font-size:14px;margin-top:-8px">(.*?)</p>'
PHOTO_RUN = re.compile(rf"(?:{IMG_P}\s*(?:{CAP_P}\s*)?){{2,}}", re.S)


def _memo(m):
    cells = CELL.findall(m.group(1))
    if len(cells) < 2:
        return m.group(0)
    lines = [f'<p style="{S["memo_name"]}">{cells[1]}</p>']
    for label, value in zip(cells[2::2], cells[3::2]):
        lines.append(f'<p style="{S["memo_line"]}">{label} : {value}</p>' if label.strip() else f'<p style="{S["memo_line"]}">{value}</p>')
    return f'<div style="{S["memo"]}">{"".join(lines)}<span style="{S["fold"]}"></span></div>'


def _photos(m):
    run = m.group(0)
    imgs = re.findall(r"<img [^>]*>", run)
    caps = [c for c in re.findall(CAP_P, run, re.S) if c.strip()]
    imgs = [re.sub(r'\s(?:width="\d+"|style="[^"]*")', "", i).replace("<img ", f'<img style="{S["photo_img"]}" ', 1) for i in imgs]
    rows = []
    for i in range(0, len(imgs), 2):
        pair = imgs[i:i + 2]
        if len(pair) == 2:
            rows.append("<tr>" + "".join(f'<td style="{S["photo_td"]};width:50%">{x}</td>' for x in pair) + "</tr>")
        else:
            rows.append(f'<tr><td colspan="2" style="{S["photo_td"]}">{pair[0]}</td></tr>')
    out = f'<table style="{S["photos"]}"><tbody>{"".join(rows)}</tbody></table>'
    if caps:
        out += f'<p style="{S["caption"]}">{" · ".join(caps)}</p>'
    return out


def _table(m):
    """보통 표(목차·일정·비교): 가운데, 첫 줄은 연두 머리 칸."""
    rows = re.findall(r"<tr>(.*?)</tr>", m.group(0), re.S)
    out = []
    for n, row in enumerate(rows):
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)
        tag, style = ("th", S["th"]) if n == 0 else ("td", S["td"])
        cells = [re.sub(r"</?strong>", "", c) if n == 0 else c for c in cells]
        out.append("<tr>" + "".join(f'<{tag} style="{style}">{c.strip()}</{tag}>' for c in cells) + "</tr>")
    return f'<table style="{S["table"]}"><tbody>{"".join(out)}</tbody></table>'


def yudi_html(body_html):
    """티스토리용 HTML(tistory_html 결과) → 유디 메모지 모양. 빈 줄 문단은 빼고 간격은 각 블록의 margin 이 맡는다."""
    out = body_html.replace(GAP, "")
    out = CARD.sub(_memo, out)
    out = PHOTO_RUN.sub(_photos, out)
    out = re.sub(r"<table(?! style=\"(?:" + re.escape(S["photos"]) + r"))[^>]*>.*?</table>", _table, out, flags=re.S)
    out = re.sub(r"<blockquote[^>]*>(.*?)</blockquote>",
                 lambda m: f'<div style="{S["lead"]}">' + re.sub(r"<p[^>]*>", f'<p style="{S["lead_p"]}">', m.group(1)) + "</div>",
                 out, flags=re.S)
    out = re.sub(r"<h2[^>]*>", f'<p style="{S["quote"]}">“</p><h2 style="{S["h2"]}">', out)
    out = re.sub(r"<h3[^>]*>", f'<h3 style="{S["h3"]}">', out)
    out = re.sub(r"<hr[^>]*>", f'<p style="{S["cut"]}">／</p>', out)
    out = re.sub(r"<p>", f'<p style="{S["p"]}">', out)
    out = re.sub(CAP_P, lambda m: f'<p style="{S["caption"]}">{m.group(1)}</p>', out)
    out = re.sub(r"<strong>", f'<strong style="{S["strong"]}">', out)
    out = re.sub(r"<u>(.*?)</u>", lambda m: f'<span style="{S["mark"]}">{m.group(1)}</span>', out, flags=re.S)
    out = re.sub(r"<a (?![^>]*\bstyle=)", f'<a style="{S["a"]}" ', out)
    return f'<div style="{S["wrap"]}">\n{out}\n</div>'


PROMPT = """## 글 모양 — 유디 메모지 (이 카테고리만, 2026-10-23 사용자: 내용이 아니라 화면 짜임을 유디 블로그처럼)
모양(가운데 정렬·글꼴·색·메모지 상자·사선)은 붙여 넣는 HTML 이 그린다. 변환본은 아래처럼 '쓰기만' 한다 (HTML·글꼴·색 코드는 넣지 않는다).
- 한 줄에 한 호흡: 문장을 의미 단위로 끊어 줄을 바꾼다 (한 줄 15~25자 안팎, 2~4줄이 한 단락, 단락 사이는 빈 줄). 가운데 정렬로 보인다.
- 굵게(**)는 청록 글자로 보인다 — 한 단락에 많아야 한 번, 꼭 짚을 숫자·이름에만. 가장 중요한 한 구절은 ==형광펜== (한 소제목에 한 번 이하).
- 소제목(##)은 번호를 단 짧은 물음·말 ("1. 공항에서 난바까지는 어떻게 가요?"). 회색 큰따옴표 + 명조 + 밑줄로 보인다. ### 는 장소 이름처럼 짧게.
- 큰 단락(일차·주제)이 바뀔 때 `---` 한 줄 (가운데 사선으로 보인다).
- 정보 카드(::: 장소|맛집 …)는 그대로 쓴다 — 모서리 접힌 메모지 상자(청록 글자)로 보인다. 이름표는 짧게 (📍 위치 · ⏰ 운영 시간 · 💴 입장료 · 🚃 가는 법 · 🗺️ 지도).
- 사진은 장소마다 2~4장을 연달아 두면 2장씩 붙은 콜라주가 된다 (한 장만 있으면 한 장). 사진 설명 줄은 작은 회색으로 모인다.
- 목차는 맨 위 인용 다음에 1열 표 하나 (머리 칸 '목차', 항목은 소제목 번호 그대로). 표는 가운데, 머리 줄은 연두.
- 맨 위 인용 상자(>)는 2~3줄 짧게 — 위아래 가는 선 사이 가운데 글로 보인다.
- 이모지는 줄 앞 표시로 조금 (💡 팁, ✔️ 추천, ❌ 주의, 👇🏻 아래 안내)."""
