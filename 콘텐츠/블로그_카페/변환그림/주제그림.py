"""총정리 글의 주제 그림 — 그 주제를 장면으로 그린 일러스트 (2026-10-31 사용자: 예시 dhsy.tistory.com/420 처럼 주제를 그림으로.
PT 처럼 표를 옮긴 그림은 쓰지 않는다. 예시는 축제라 화려했을 뿐 — 스타일은 주제마다 맞게, 차분하게).
python 주제그림.py <설계 json> <저장할 png>
  설계 json:
    {"theme": "ai_tool | ai_month | it_sale", "kind": "cover | section",
     "badge": "2026년 11월", "title": "용도별 *무료 AI*\\n총정리", "sub": "이미지 · 영상 · PPT · 글쓰기",
     "label": "11월"(장면 속 달력·태그 글자, 없어도 됨),
     "items": [{"title", "scene", "rows": [[아이콘, 이름표, 값]], "note"}]  ← section 만, 2칸}
  title 의 *말* 은 포인트 색, \\n 은 줄바꿈.
  cover: 맨 위 인용 다음 대표 그림. theme 마다 장면이 정해져 있다 —
    ai_tool  노트북에서 이미지 · 영상 · PPT · 문서 창이 떠오르는 책상 (청록, 맑게)
    ai_month 큰 달력 + 겹쳐 뜬 AI 창들 + 손 흔드는 로봇 (빨강 포인트, 단정하게)
    it_sale  할인 화면 노트북 · 택배 상자 · 쇼핑백 · 가격표가 놓인 책상 (주황, 따뜻하게)
  section: 번호 칸 2개, 칸마다 작은 장면 + 정보 3~4줄. scene 이름:
    image · video · slides · writing · code · voice · chat · bot · calendar · parcel · laptop · keyboard · bag · tag
  rows 아이콘: lucide 0.344 이름 (calendar · credit-card · globe · shopping-cart · badge-percent · alert-triangle · gift · clock …)
그림 속 날짜·숫자는 사실 점검을 마친 것만. 장면은 직접 그린 평면 일러스트라 실제 사진처럼 보이지 않는다 — 실제 사진은 글에 따로 넣는다.
만드는 법은 다른 가공이미지와 같다: HTML(SVG) → 크롬 헤드리스 캡처 → PIL 로 1200px·내용 높이만 자른다.
"""
import argparse
import html
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
FONT = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
ICONS = "https://cdn.jsdelivr.net/npm/lucide@0.344.0/dist/umd/lucide.min.js"
W = 1200

# bg 바탕 · bg2 진한 바탕(책상) · main 포인트 · main2 밝은 포인트 · accent 작은 반대색 · ink 글자 · line 선
THEMES = {
    "ai_tool": dict(bg="#eaf6f3", bg2="#cfe9e2", main="#0f766e", main2="#2bb3a3", accent="#f2a93b", ink="#1d2b29",
                    ink2="#5b6b68", line="#bfdcd4", dark="#24332f", kraft="#d9a86c"),
    "ai_month": dict(bg="#faf3f1", bg2="#f1dcd7", main="#e03131", main2="#ff8a8a", accent="#3b5bdb", ink="#2a2120",
                     ink2="#6e5f5c", line="#ecccc6", dark="#2f2a2a", kraft="#d9a86c"),
    "it_sale": dict(bg="#fdf4ec", bg2="#f6dfc9", main="#e8590c", main2="#ffa25c", accent="#1c7ed6", ink="#2c231d",
                    ink2="#6f6157", line="#efd3bb", dark="#2e2925", kraft="#d6a265"),
}


# ---------------------------------------------------------------- 작은 조각
def shadow(cx, cy, rx, ry=None):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry or rx * 0.16:.1f}" fill="#000" opacity=".08"/>'


def sparkle(cx, cy, r, color):
    return (f'<path d="M{cx} {cy - r} Q{cx} {cy} {cx + r} {cy} Q{cx} {cy} {cx} {cy + r} Q{cx} {cy} {cx - r} {cy} '
            f'Q{cx} {cy} {cx} {cy - r}Z" fill="{color}"/>')


def blob(cx, cy, r, color, op=1):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" opacity="{op}"/>'


def rot(svg, angle, cx, cy):
    return f'<g transform="rotate({angle} {cx} {cy})">{svg}</g>'


def text(x, y, s, size, color, weight=800, anchor="middle"):
    return (f'<text x="{x}" y="{y}" font-family="Pretendard" font-size="{size}" font-weight="{weight}" fill="{color}" '
            f'text-anchor="{anchor}" dominant-baseline="central">{html.escape(s)}</text>')


# ---------------------------------------------------------------- 창 안의 그림 (x, y, w, h 상자 안)
def g_image(x, y, w, h, p):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{p["bg2"]}"/>'
            f'<circle cx="{x + w * .74}" cy="{y + h * .3}" r="{h * .13}" fill="{p["accent"]}"/>'
            f'<path d="M{x} {y + h} L{x + w * .32} {y + h * .45} L{x + w * .55} {y + h * .78} L{x + w * .7} {y + h * .58} '
            f'L{x + w} {y + h}Z" fill="{p["main"]}"/>'
            f'<path d="M{x + w * .45} {y + h} L{x + w * .7} {y + h * .58} L{x + w} {y + h}Z" fill="{p["main2"]}"/>')


def g_video(x, y, w, h, p):
    cx, cy, r = x + w / 2, y + h * .45, h * .2
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{p["dark"]}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{p["main"]}"/>'
            f'<path d="M{cx - r * .32} {cy - r * .45} L{cx + r * .5} {cy} L{cx - r * .32} {cy + r * .45}Z" fill="#fff"/>'
            f'<rect x="{x + w * .08}" y="{y + h * .84}" width="{w * .84}" height="5" rx="2.5" fill="#ffffff" opacity=".25"/>'
            f'<rect x="{x + w * .08}" y="{y + h * .84}" width="{w * .38}" height="5" rx="2.5" fill="{p["main2"]}"/>')


def g_slides(x, y, w, h, p):
    bars = [.45, .7, .55, .9]
    bw = w * .12
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fff"/>',
           f'<rect x="{x + w * .08}" y="{y + h * .1}" width="{w * .45}" height="8" rx="4" fill="{p["ink"]}" opacity=".75"/>']
    for i, b in enumerate(bars):
        bh = h * .55 * b
        out.append(f'<rect x="{x + w * .12 + i * bw * 1.7}" y="{y + h * .9 - bh}" width="{bw}" height="{bh}" rx="3" '
                   f'fill="{p["main"] if i == 3 else p["main2"]}"/>')
    return "".join(out)


def g_doc(x, y, w, h, p):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fff"/>']
    for i, ln in enumerate([.7, .9, .82, .6, .88, .5]):
        color = p["main"] if i == 2 else "#d5dbda"
        out.append(f'<rect x="{x + w * .08}" y="{y + h * .12 + i * h * .14}" width="{w * .84 * ln}" height="7" rx="3.5" fill="{color}"/>')
    return "".join(out)


def g_code(x, y, w, h, p):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{p["dark"]}"/>']
    rows = [(0, .35, p["main2"]), (1, .5, "#ffffff"), (1, .3, p["accent"]), (2, .4, "#ffffff"), (1, .25, p["main2"]), (0, .2, "#ffffff")]
    for i, (ind, ln, c) in enumerate(rows):
        out.append(f'<rect x="{x + w * .08 + ind * w * .07}" y="{y + h * .13 + i * h * .13}" width="{w * ln}" height="6" rx="3" '
                   f'fill="{c}" opacity="{.9 if c != "#ffffff" else .55}"/>')
    return "".join(out)


def g_chat(x, y, w, h, p):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fff"/>'
            f'<rect x="{x + w * .06}" y="{y + h * .12}" width="{w * .55}" height="{h * .24}" rx="{h * .1}" fill="{p["bg2"]}"/>'
            f'<rect x="{x + w * .39}" y="{y + h * .44}" width="{w * .55}" height="{h * .24}" rx="{h * .1}" fill="{p["main"]}"/>'
            f'<rect x="{x + w * .06}" y="{y + h * .74}" width="{w * .35}" height="{h * .16}" rx="{h * .08}" fill="{p["bg2"]}"/>')


def g_voice(x, y, w, h, p):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fff"/>']
    n = 13
    for i in range(n):
        bh = h * (.18 + .55 * abs(math.sin(i * .9)))
        out.append(f'<rect x="{x + w * .1 + i * w * .8 / n}" y="{y + h / 2 - bh / 2}" width="{w * .035}" height="{bh}" rx="3" '
                   f'fill="{p["main"] if i % 4 else p["main2"]}"/>')
    return "".join(out)


def g_prompt(x, y, w, h, p):
    """노트북 화면: 가운데 입력창 + 만들기 단추 + 반짝이"""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#fff"/>'
            + sparkle(x + w / 2, y + h * .27, h * .12, p["main2"])
            + f'<rect x="{x + w * .2}" y="{y + h * .45}" width="{w * .6}" height="10" rx="5" fill="#d5dbda"/>'
            f'<rect x="{x + w * .12}" y="{y + h * .62}" width="{w * .76}" height="{h * .2}" rx="{h * .1}" fill="{p["bg"]}" '
            f'stroke="{p["line"]}" stroke-width="2"/>'
            f'<circle cx="{x + w * .8}" cy="{y + h * .72}" r="{h * .07}" fill="{p["main"]}"/>')


def g_sale(x, y, w, h, p):
    """노트북 화면: 큰 가격표와 지운 값"""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#fff"/>'
            + tag(x + w * .3, y + h * .5, h * .55, p, "%", -12)
            + f'<rect x="{x + w * .55}" y="{y + h * .3}" width="{w * .3}" height="9" rx="4.5" fill="#d5dbda"/>'
            f'<line x1="{x + w * .53}" y1="{y + h * .33}" x2="{x + w * .87}" y2="{y + h * .33}" stroke="{p["ink2"]}" stroke-width="3"/>'
            f'<rect x="{x + w * .55}" y="{y + h * .48}" width="{w * .24}" height="14" rx="7" fill="{p["main"]}"/>'
            f'<rect x="{x + w * .55}" y="{y + h * .7}" width="{w * .32}" height="{h * .14}" rx="{h * .07}" fill="{p["dark"]}"/>')


GLYPHS = {"image": g_image, "video": g_video, "slides": g_slides, "writing": g_doc, "code": g_code, "chat": g_chat,
          "voice": g_voice, "prompt": g_prompt, "sale": g_sale}


# ---------------------------------------------------------------- 사물
def window(x, y, w, h, p, glyph, angle=0, floor=True):
    bar = 24
    body = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#fff" stroke="{p["line"]}" stroke-width="2"/>'
            f'<path d="M{x} {y + 14} a14 14 0 0 1 14 -14 h{w - 28} a14 14 0 0 1 14 14 v{bar - 14} h{-w}Z" fill="{p["bg2"]}"/>'
            + "".join(f'<circle cx="{x + 16 + i * 14}" cy="{y + bar / 2}" r="4" fill="{c}"/>'
                      for i, c in enumerate([p["main"], p["accent"], "#ffffff"]))
            + GLYPHS[glyph](x + 12, y + bar + 10, w - 24, h - bar - 22, p))
    return (shadow(x + w / 2, y + h + 26, w * .38) if floor else "") + rot(body, angle, x + w / 2, y + h / 2)


def laptop(x, y, w, p, glyph):
    h = w * .62
    return (shadow(x + w / 2, y + h + w * .07, w * .62)
            + f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{p["dark"]}"/>'
            + GLYPHS[glyph](x + 14, y + 14, w - 28, h - 28, p)
            + f'<path d="M{x - w * .1} {y + h} H{x + w * 1.1} L{x + w * 1.04} {y + h + w * .055} H{x - w * .04}Z" fill="#c9d2d0"/>'
            f'<rect x="{x + w * .42}" y="{y + h}" width="{w * .16}" height="{w * .018}" rx="3" fill="#aab4b2"/>')


def bot(cx, cy, s, p, wave=True):
    hw, hh = 70 * s, 56 * s
    arm = (f'<path d="M{cx + hw * .62} {cy + hh * .95} q{28 * s} {-10 * s} {34 * s} {-46 * s}" stroke="{p["main2"]}" '
           f'stroke-width="{11 * s}" stroke-linecap="round" fill="none"/>' if wave else "")
    return (shadow(cx, cy + hh * 1.75, 60 * s)
            + f'<rect x="{cx - hw * .55}" y="{cy + hh * .55}" width="{hw * 1.1}" height="{hh * 1.05}" rx="{18 * s}" fill="{p["main2"]}"/>'
            + arm
            + f'<line x1="{cx}" y1="{cy - hh * .62}" x2="{cx}" y2="{cy - hh * .95}" stroke="{p["ink"]}" stroke-width="{4 * s}"/>'
            f'<circle cx="{cx}" cy="{cy - hh}" r="{8 * s}" fill="{p["accent"]}"/>'
            f'<rect x="{cx - hw / 2}" y="{cy - hh * .62}" width="{hw}" height="{hh * 1.25}" rx="{22 * s}" fill="{p["main"]}"/>'
            f'<rect x="{cx - hw * .38}" y="{cy - hh * .42}" width="{hw * .76}" height="{hh * .82}" rx="{16 * s}" fill="#fff"/>'
            f'<circle cx="{cx - hw * .16}" cy="{cy - hh * .05}" r="{6 * s}" fill="{p["ink"]}"/>'
            f'<circle cx="{cx + hw * .16}" cy="{cy - hh * .05}" r="{6 * s}" fill="{p["ink"]}"/>'
            f'<path d="M{cx - hw * .1} {cy + hh * .17} q{hw * .1} {hh * .12} {hw * .2} 0" stroke="{p["ink"]}" stroke-width="{3 * s}" '
            f'fill="none" stroke-linecap="round"/>')


def calendar(x, y, w, h, p, label, hot=(3, 10, 18, 24, 28)):
    head = h * .22
    out = [shadow(x + w / 2, y + h + 22, w * .46),
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="#fff" stroke="{p["line"]}" stroke-width="2"/>',
           f'<path d="M{x} {y + 18} a18 18 0 0 1 18 -18 h{w - 36} a18 18 0 0 1 18 18 v{head - 18} h{-w}Z" fill="{p["main"]}"/>',
           text(x + w / 2, y + head / 2 + 2, label, head * .48, "#fff")]
    for i in (.25, .75):
        out.append(f'<rect x="{x + w * i - 6}" y="{y - 14}" width="12" height="30" rx="6" fill="{p["ink"]}"/>')
    cols, rows = 7, 5
    gw, gh = (w - 40) / cols, (h - head - 30) / rows
    for r in range(rows):
        for c in range(cols):
            d = r * cols + c + 1
            if d > 30:
                continue
            cx, cy = x + 20 + c * gw + gw / 2, y + head + 15 + r * gh + gh / 2
            if d in hot:
                out.append(f'<circle cx="{cx}" cy="{cy}" r="{min(gw, gh) * .4}" fill="{p["main"] if d == hot[2] else p["main2"]}"/>')
            else:
                out.append(f'<rect x="{cx - gw * .28}" y="{cy - gh * .2}" width="{gw * .56}" height="{gh * .4}" rx="4" fill="{p["bg"]}"/>')
    return "".join(out)


def parcel(x, y, s, p):
    w, h, t = 150 * s, 110 * s, 34 * s
    return (shadow(x + w / 2 + t / 2, y + h + 6 * s, w * .62)
            + f'<path d="M{x} {y} l{t} {-t * .7} h{w} l{-t} {t * .7}Z" fill="#e6be8a"/>'
            f'<path d="M{x + w} {y} l{t} {-t * .7} v{h} l{-t} {t * .7}Z" fill="#c0894c"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{p["kraft"]}"/>'
            f'<rect x="{x + w * .42}" y="{y}" width="{w * .16}" height="{h}" fill="#f1d5ac"/>'
            f'<path d="M{x + w * .42 + t * .0} {y} l{t} {-t * .7} h{w * .16} l{-t} {t * .7}Z" fill="#f6e2c4"/>'
            f'<rect x="{x + w * .1}" y="{y + h * .62}" width="{w * .22}" height="{h * .2}" rx="3" fill="#fff" opacity=".85"/>')


def tag(cx, cy, s, p, label, angle=0):
    w, h = s * 1.5, s
    x, y = cx - w / 2, cy - h / 2
    body = (f'<path d="M{x + h * .38} {y} H{x + w} a8 8 0 0 1 8 8 V{y + h - 8} a8 8 0 0 1 -8 8 H{x + h * .38} L{x} {cy}Z" '
            f'fill="{p["main"]}"/>'
            f'<circle cx="{x + h * .34}" cy="{cy}" r="{h * .09}" fill="#fff"/>'
            + text(x + w * .6 + 4, cy + 1, label, h * (.5 if len(label) < 3 else .34), "#fff", 900))
    return rot(body, angle, cx, cy)


def keyboard(x, y, w, p):
    h = w * .3
    out = [shadow(x + w / 2, y + h + 8, w * .5),
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#e9eeed" stroke="#d3dad8" stroke-width="2"/>']
    kw = (w - 24) / 12
    for r in range(3):
        for c in range(12):
            out.append(f'<rect x="{x + 12 + c * kw + 2}" y="{y + 10 + r * (h - 20) / 3 + 2}" width="{kw - 4}" '
                       f'height="{(h - 20) / 3 - 4}" rx="3" fill="#fff"/>')
    return "".join(out)


def mouse(cx, cy, s, p):
    return (shadow(cx, cy + 34 * s, 30 * s)
            + f'<rect x="{cx - 22 * s}" y="{cy - 32 * s}" width="{44 * s}" height="{64 * s}" rx="{22 * s}" fill="#e9eeed" '
            f'stroke="#d3dad8" stroke-width="2"/><line x1="{cx}" y1="{cy - 32 * s}" x2="{cx}" y2="{cy - 8 * s}" stroke="#d3dad8" stroke-width="2"/>')


def bag(x, y, w, h, p):
    return (shadow(x + w / 2, y + h + 6, w * .6)
            + f'<path d="M{x + w * .3} {y + h * .18} v{-h * .1} a{w * .2} {w * .2} 0 0 1 {w * .4} 0 v{h * .1}" stroke="{p["ink"]}" '
            f'stroke-width="6" fill="none"/>'
            f'<path d="M{x} {y + h * .18} H{x + w} L{x + w * .94} {y + h} H{x + w * .06}Z" fill="{p["main2"]}"/>'
            f'<rect x="{x}" y="{y + h * .18}" width="{w}" height="{h * .08}" fill="{p["main"]}"/>')


def plant(x, y, s, p):
    leaves = "".join(rot(f'<ellipse cx="{x}" cy="{y - 60 * s}" rx="{13 * s}" ry="{38 * s}" fill="{c}"/>', a, x, y - 22 * s)
                     for a, c in ((-38, p["main"]), (0, p["main2"]), (38, p["main"])))
    return (leaves + f'<path d="M{x - 30 * s} {y - 28 * s} H{x + 30 * s} L{x + 22 * s} {y} H{x - 22 * s}Z" fill="{p["kraft"]}"/>')


def cup(x, y, s, p):
    return (f'<path d="M{x - 26 * s} {y - 56 * s} H{x + 26 * s} V{y - 8 * s} a10 10 0 0 1 -10 10 H{x - 16 * s} a10 10 0 0 1 -10 -10Z" '
            f'fill="#fff" stroke="{p["line"]}" stroke-width="2"/>'
            f'<path d="M{x + 26 * s} {y - 46 * s} a14 14 0 0 1 0 28" stroke="{p["line"]}" stroke-width="5" fill="none"/>'
            + "".join(f'<path d="M{x + dx * s} {y - 66 * s} q8 -12 0 -24 q-8 -12 0 -24" stroke="{p["ink2"]}" stroke-width="3" '
                      f'fill="none" opacity=".35" stroke-linecap="round"/>' for dx in (-9, 9)))


def dots(x1, y1, x2, y2, p):
    return (f'<path d="M{x1} {y1} Q{(x1 + x2) / 2} {min(y1, y2) - 40} {x2} {y2}" stroke="{p["main2"]}" stroke-width="3" '
            f'stroke-dasharray="2 10" stroke-linecap="round" fill="none"/>')


def desk(y, p):
    return f'<rect x="0" y="{y}" width="{W}" height="400" fill="{p["bg2"]}"/><rect x="0" y="{y}" width="{W}" height="6" fill="{p["line"]}"/>'


# ---------------------------------------------------------------- 표지 장면 (1200 × 900)
def cover_ai_tool(p, label):
    return "".join([
        blob(120, 160, 90, p["bg2"], .6), blob(1090, 220, 120, p["bg2"], .6), desk(800, p),
        dots(600, 600, 230, 470, p), dots(600, 600, 980, 470, p), dots(560, 640, 200, 650, p), dots(640, 640, 1000, 650, p),
        window(100, 420, 230, 160, p, "image", -5, False), window(870, 405, 240, 165, p, "video", 5, False),
        window(80, 610, 215, 150, p, "slides", 4, False), window(905, 600, 215, 150, p, "writing", -4, False),
        laptop(430, 560, 340, p, "prompt"),
        plant(360, 808, .9, p), cup(845, 808, .9, p),
        sparkle(395, 470, 16, p["accent"]), sparkle(820, 455, 12, p["main2"]), sparkle(600, 395, 10, p["main"]),
    ])


def cover_ai_month(p, label):
    return "".join([
        blob(1080, 150, 110, p["bg2"], .6), blob(110, 250, 80, p["bg2"], .6), desk(810, p),
        calendar(110, 440, 450, 330, p, label or "이달"),
        window(615, 420, 300, 170, p, "chat", -3, False), window(675, 520, 300, 170, p, "image", 2, False),
        window(735, 620, 290, 165, p, "code", -2),
        bot(1095, 640, 1.05, p),
        sparkle(600, 430, 14, p["accent"]), sparkle(1010, 445, 12, p["main"]), sparkle(80, 420, 10, p["main2"]),
    ])


def cover_it_sale(p, label):
    return "".join([
        blob(120, 180, 100, p["bg2"], .6), blob(1100, 160, 90, p["bg2"], .6), desk(800, p),
        parcel(70, 660, 1.2, p), parcel(130, 560, .8, p),
        laptop(450, 560, 320, p, "sale"),
        bag(880, 590, 170, 210, p),
        tag(1035, 520, 64, p, "%", 14), tag(370, 470, 52, p, label or "SALE", -14),
        keyboard(470, 812, 250, p), mouse(780, 848, .75, p),
        sparkle(840, 470, 14, p["accent"]), sparkle(620, 420, 10, p["main"]), sparkle(300, 600, 9, p["main2"]),
    ])


COVERS = {"ai_tool": cover_ai_tool, "ai_month": cover_ai_month, "it_sale": cover_it_sale}


# ---------------------------------------------------------------- 칸 장면 (520 × 230)
def small(scene, p, label):
    base = blob(90, 70, 46, p["bg2"]) + blob(450, 170, 60, p["bg2"])
    if scene in GLYPHS:
        art = window(130, 34, 260, 160, p, scene) + sparkle(420, 60, 14, p["accent"]) + sparkle(100, 170, 10, p["main2"])
    elif scene == "bot":
        art = window(70, 40, 230, 140, p, "chat", -3) + bot(390, 110, .9, p)
    elif scene == "calendar":
        art = calendar(160, 40, 200, 160, p, label or "이달") + sparkle(410, 70, 13, p["accent"])
    elif scene == "parcel":
        art = parcel(120, 110, .9, p) + parcel(270, 120, .7, p) + tag(410, 70, 44, p, "%", 12)
    elif scene == "laptop":
        art = laptop(160, 34, 200, p, "sale") + sparkle(420, 60, 12, p["accent"])
    elif scene == "keyboard":
        art = keyboard(100, 90, 260, p) + mouse(410, 130, .8, p) + sparkle(430, 50, 12, p["accent"])
    elif scene == "bag":
        art = bag(190, 30, 140, 170, p) + tag(390, 80, 50, p, "%", 10) + sparkle(120, 70, 12, p["accent"])
    elif scene == "tag":
        art = tag(200, 110, 70, p, "%", -10) + tag(350, 90, 50, p, label or "SALE", 12) + sparkle(110, 60, 12, p["accent"])
    else:
        raise SystemExit(f"모르는 scene: {scene}")
    return f'<svg viewBox="0 0 520 230" width="100%">{base}{art}</svg>'


# ---------------------------------------------------------------- 페이지
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{margin:0;background:#fff;font-family:Pretendard,sans-serif;-webkit-font-smoothing:antialiased}
.cv{position:relative;width:1200px;height:900px;background:var(--bg);overflow:hidden}
.cv svg.scene{position:absolute;left:0;top:0}
.cv .head{position:absolute;left:0;right:0;top:58px;text-align:center}
.badge{display:inline-block;background:#fff;color:var(--main);border:2px solid var(--main);border-radius:999px;padding:8px 22px;
       font-size:24px;font-weight:800}
.cv h1{font-size:84px;font-weight:900;line-height:1.12;letter-spacing:-.03em;color:var(--ink);margin-top:20px}
h1 em{font-style:normal;color:var(--main)}
.cv .sub{display:inline-block;margin-top:20px;background:#fff;border-radius:999px;padding:10px 24px;font-size:24px;font-weight:600;
         color:var(--ink2);box-shadow:0 2px 0 var(--line)}
.sec{width:1200px;background:var(--bg);padding:52px 48px 48px}
.sec .head{text-align:center}
.sec h1{font-size:60px;font-weight:900;line-height:1.15;letter-spacing:-.03em;color:var(--ink);margin-top:16px}
.sec .sub{margin-top:12px;font-size:23px;color:var(--ink2);font-weight:600}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:36px}
.pn{background:#fff;border-radius:24px;padding:24px 24px 22px;box-shadow:0 3px 0 var(--line)}
.pn .t{display:flex;align-items:center;gap:14px}
.pn .no{width:46px;height:46px;border-radius:50%;background:var(--main);color:#fff;font-size:25px;font-weight:900;
        display:flex;align-items:center;justify-content:center;flex:none}
.pn .t b{font-size:32px;font-weight:900;color:var(--ink);letter-spacing:-.02em}
.pn .art{background:var(--bg);border-radius:18px;margin:18px 0 10px}
.pn .row{display:flex;align-items:center;gap:12px;padding:9px 0;font-size:21px}
.pn .row .ri{width:26px;height:26px;color:var(--main);flex:none}
.pn .row .k{background:var(--bg);color:var(--main);font-weight:800;border-radius:8px;padding:4px 12px;flex:none;min-width:96px;text-align:center}
.pn .row .v{color:var(--ink);font-weight:700;line-height:1.35}
.pn .note{margin-top:12px;background:var(--bg);border-radius:12px;padding:13px 16px;font-size:19px;line-height:1.5;color:var(--ink2)}
"""


def title_html(s):
    out = html.escape(s or "", quote=False).replace("\\n", "\n").replace("\n", "<br>")
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", out)


def cover(spec, p):
    sub = f'<div class="sub">{html.escape(spec["sub"])}</div>' if spec.get("sub") else ""
    badge = f'<div class="badge">{html.escape(spec["badge"])}</div>' if spec.get("badge") else ""
    scene = COVERS[spec["theme"]](p, spec.get("label"))
    return (f'<div class="cv"><svg class="scene" viewBox="0 0 1200 900" width="1200" height="900">{scene}</svg>'
            f'<div class="head">{badge}<h1>{title_html(spec.get("title"))}</h1>{sub}</div></div>')


def section(spec, p):
    cols = []
    for i, it in enumerate(spec["items"], 1):
        rows = "".join(f'<div class="row"><i data-lucide="{html.escape(ic)}" class="ri"></i><span class="k">{html.escape(k)}</span>'
                       f'<span class="v">{html.escape(v)}</span></div>' for ic, k, v in it.get("rows", []))
        note = f'<div class="note">{html.escape(it["note"])}</div>' if it.get("note") else ""
        cols.append(f'<div class="pn"><div class="t"><div class="no">{i}</div><b>{html.escape(it["title"])}</b></div>'
                    f'<div class="art">{small(it["scene"], p, it.get("label"))}</div>{rows}{note}</div>')
    badge = f'<div class="badge">{html.escape(spec["badge"])}</div>' if spec.get("badge") else ""
    sub = f'<div class="sub">{html.escape(spec["sub"])}</div>' if spec.get("sub") else ""
    return f'<div class="sec"><div class="head">{badge}<h1>{title_html(spec.get("title"))}</h1>{sub}</div><div class="cols">{"".join(cols)}</div></div>'


def page(spec):
    p = THEMES[spec["theme"]]
    body = cover(spec, p) if spec.get("kind", "cover") == "cover" else section(spec, p)
    var = ";".join(f"--{k}:{v}" for k, v in p.items())
    return (f'<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="{FONT}"><style>{CSS}</style>'
            f'<body style="{var}">{body}<script src="{ICONS}"></script><script>lucide.createIcons()</script></body>')


def shoot(doc, out):
    tmp = Path(tempfile.mkdtemp())
    src = tmp / "art.html"
    src.write_text(doc, encoding="utf-8")
    shot = tmp / "shot.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--user-data-dir={tmp / 'prof'}", "--window-size=1260,1800", "--virtual-time-budget=8000",
                    f"--screenshot={shot}", src.as_uri()], check=True, capture_output=True)
    im = Image.open(shot).convert("RGB").crop((0, 0, W, 1800))
    gray = im.convert("L")
    bottom = next(y for y in range(im.height - 1, 0, -1) if gray.crop((0, y, W, y + 1)).getextrema() not in ((0, 0), (255, 255)))
    im = im.crop((0, 0, W, bottom + 1))
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path, help="설계 json (UTF-8)")
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    shoot(page(json.loads(a.spec.read_text(encoding="utf-8"))), a.out)
    print(a.out)


if __name__ == "__main__":
    main()
