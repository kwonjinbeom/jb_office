"""총정리 글의 정리 그림 — 회사 PT 슬라이드처럼 정적이고 깔끔하게 (2026-10-31 사용자: memorily 총정리 카테고리.
예시 블로그(dhsy.tistory.com/420)처럼 한눈에 정보가 들어오되, '뽕짝' 없이 흰 바탕 · 포인트 색 하나 · 얇은 선).
python 정리카드.py <설계 json> <저장할 png>
  설계 json: {"theme", "kicker", "title", "sub", "foot", "layout", "items", ...}
  theme: ai_tool(청록 · 무료 AI 툴) · ai_month(빨강 · 이달의 AI) · it_sale(주황 · IT 할인) · plain(회색)
  layout (칸 수는 items 개수대로):
    grid     한눈에 — {"icon", "label", "main", "note", "tag"} 2~6칸. 표지·용도별 지도
    panels   번호 칸 — {"title", "photo"(주소, 없어도 됨), "rows": [[아이콘, 이름표, 값]], "note"} 2~3칸
    timeline 달력 — {"date", "title", "note", "hot"} 3~7개. 행사·발표 날짜
    compare  비교 — "columns": [...], items {"name", "cells": [...]} · 칸 값 O · △ · X 는 점으로, 나머지는 글
    pick     고르기 — {"if", "then", "note"} 3~5줄. '이럴 때 → 이것'
    number   핵심 숫자 — "big": {"value", "unit", "label"} + items {"value", "label"} 2~4개
  icon: lucide 아이콘 이름 (image · video · presentation · pen-line · code · mic · calendar · tag · shopping-cart · gift ·
        clock · badge-percent · globe · sparkles · cpu · bot · credit-card · alert-triangle · check-circle …, lucide 0.344 이름)
그림 속 숫자·날짜는 사실 점검을 마친 것만 넣는다. 사진(panels 의 photo)은 글에 쓰는 사진과 같은 기준 — 무료 사진 · 공식 보도 이미지 · 직접 찍은 화면.
만드는 법은 다른 가공이미지와 같다: HTML → 크롬 헤드리스 캡처 → PIL 로 1200px·내용 높이만 자른다 (16:9 이상, 내용이 많으면 길어진다).
"""
import argparse
import html
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
FONT = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
ICONS = "https://cdn.jsdelivr.net/npm/lucide@0.344.0/dist/umd/lucide.min.js"
W, MIN_H = 1200, 675

# 포인트 색 하나 + 그 연한 바탕. 나머지는 모두 같은 회색 (글자 #1f2328 · 보조 #6b7280 · 선 #e5e7eb)
THEMES = {
    "ai_tool": ("#0f766e", "#e8f4f1"),
    "ai_month": ("#e03131", "#fdeeee"),  # memorily › AI 의 빨강 (0021)
    "it_sale": ("#d9480f", "#fdf1e9"),
    "plain": ("#495057", "#f1f3f5"),
}

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{margin:0;background:#fff;font-family:Pretendard,sans-serif;color:#1f2328;-webkit-font-smoothing:antialiased}
.slide{width:1200px;min-height:675px;padding:56px 64px 40px;display:flex;flex-direction:column;border-top:10px solid var(--a)}
.kicker{font-size:19px;font-weight:700;letter-spacing:.14em;color:var(--a);text-transform:uppercase}
h1{font-size:58px;font-weight:800;line-height:1.18;letter-spacing:-.02em;margin-top:14px}
.sub{font-size:25px;color:#6b7280;margin-top:12px;line-height:1.4}
.body{flex:1;margin-top:40px}
.foot{display:flex;justify-content:space-between;align-items:flex-end;border-top:1px solid #e5e7eb;margin-top:36px;padding-top:16px;
      font-size:17px;color:#9aa0a6}
.foot b{color:#c3c8ce;font-weight:800;letter-spacing:.04em}
.ic{width:30px;height:30px;color:var(--a);stroke-width:2}
/* grid */
.grid{display:grid;gap:18px}
.cell{border:1px solid #e5e7eb;border-radius:14px;padding:26px 26px 24px;background:#fff;position:relative}
.cell .top{display:flex;align-items:center;gap:12px}
.cell .icon{width:52px;height:52px;border-radius:12px;background:var(--t);display:flex;align-items:center;justify-content:center}
.cell .label{font-size:24px;font-weight:700}
.cell .tag{position:absolute;top:22px;right:22px;font-size:15px;font-weight:700;color:var(--a);background:var(--t);padding:5px 10px;border-radius:999px}
.cell .main{font-size:27px;font-weight:800;margin-top:18px;line-height:1.3}
.cell .note{font-size:19px;color:#6b7280;margin-top:8px;line-height:1.45}
/* panels */
.panels{display:grid;gap:22px}
.panel{border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;background:#fff;display:flex;flex-direction:column}
.panel .head{display:flex;align-items:center;gap:14px;padding:22px 24px 18px}
.panel .no{width:40px;height:40px;border-radius:50%;background:var(--a);color:#fff;font-size:21px;font-weight:800;display:flex;align-items:center;justify-content:center;flex:none}
.panel .title{font-size:27px;font-weight:800;line-height:1.25}
.panel img{width:100%;height:250px;object-fit:cover;display:block}
.panel .rows{padding:18px 24px 6px}
.panel .row{display:flex;align-items:center;gap:12px;padding:11px 0;border-bottom:1px solid #f0f1f3;font-size:20px}
.panel .row:last-child{border-bottom:0}
.panel .row .ic{width:24px;height:24px;flex:none}
.panel .row .k{color:#6b7280;width:110px;flex:none;font-weight:600}
.panel .row .v{font-weight:700;line-height:1.35}
.panel .pnote{margin:auto 24px 22px;background:var(--t);border-radius:10px;padding:14px 16px;font-size:18px;line-height:1.5;color:#374151}
/* timeline */
.tl{position:relative;display:grid;gap:0;padding-top:8px}
.tl:before{content:"";position:absolute;left:0;right:0;top:66px;height:3px;background:#e5e7eb}
.ev{position:relative;padding:0 10px;text-align:center}
.ev .date{font-size:24px;font-weight:800;color:#6b7280;height:44px}
.ev .dot{width:22px;height:22px;border-radius:50%;background:#fff;border:4px solid #c3c8ce;margin:10px auto 22px;position:relative;z-index:1}
.ev.hot .date{color:var(--a)}
.ev.hot .dot{border-color:var(--a);background:var(--a);box-shadow:0 0 0 7px var(--t)}
.ev .title{font-size:23px;font-weight:800;line-height:1.3}
.ev .note{font-size:18px;color:#6b7280;margin-top:8px;line-height:1.45}
/* compare */
table.cmp{width:100%;border-collapse:collapse;font-size:21px}
.cmp th{font-size:19px;color:#6b7280;font-weight:700;padding:0 10px 14px;text-align:center;border-bottom:2px solid #1f2328}
.cmp th:first-child{text-align:left}
.cmp td{padding:17px 10px;border-bottom:1px solid #e5e7eb;text-align:center;font-weight:600}
.cmp td:first-child{text-align:left;font-weight:800;font-size:22px}
.mark{display:inline-block;width:20px;height:20px;border-radius:50%;vertical-align:middle}
.mark.o{background:var(--a)}
.mark.h{border:3px solid var(--a);background:linear-gradient(90deg,var(--a) 50%,#fff 50%)}
.mark.x{width:18px;height:3px;border-radius:2px;background:#c3c8ce}
.legend{margin-top:16px;font-size:16px;color:#9aa0a6;display:flex;gap:22px;align-items:center}
.legend .mark{width:14px;height:14px;margin-right:6px}
.legend .mark.h{border-width:2px}
.legend .mark.x{width:14px;height:3px}
/* pick */
.pick{display:flex;flex-direction:column;gap:14px}
.pk{display:grid;grid-template-columns:1fr 56px 1fr;align-items:center;border:1px solid #e5e7eb;border-radius:14px;padding:20px 24px}
.pk .if{font-size:22px;color:#374151;line-height:1.4}
.pk .arrow{color:var(--a);display:flex;justify-content:center}
.pk .then{font-size:25px;font-weight:800;line-height:1.3}
.pk .then small{display:block;font-size:17px;font-weight:500;color:#6b7280;margin-top:4px}
/* number */
.num{display:grid;grid-template-columns:1.15fr 1fr;gap:28px;align-items:stretch}
.big{background:var(--t);border-radius:18px;padding:40px 36px;display:flex;flex-direction:column;justify-content:center}
.big .v{font-size:118px;font-weight:800;color:var(--a);line-height:1;letter-spacing:-.03em}
.big .v span{font-size:44px;margin-left:6px}
.big .l{font-size:25px;font-weight:700;margin-top:18px;line-height:1.4}
.stats{display:flex;flex-direction:column;gap:14px}
.st{border:1px solid #e5e7eb;border-radius:14px;padding:20px 24px;flex:1;display:flex;flex-direction:column;justify-content:center}
.st .v{font-size:40px;font-weight:800}
.st .l{font-size:19px;color:#6b7280;margin-top:6px;line-height:1.4}
"""


def e(text):
    return html.escape(str(text or ""), quote=False).replace("\n", "<br>")


def icon(name, cls="ic"):
    return f'<i data-lucide="{html.escape(name)}" class="{cls}"></i>' if name else ""


def cols(n, most=3):
    return min(n, most) if n not in (4,) else 2


def grid(spec):
    items = spec["items"]
    n = cols(len(items))
    cells = []
    for it in items:
        tag = f'<div class="tag">{e(it.get("tag"))}</div>' if it.get("tag") else ""
        cells.append(f'<div class="cell">{tag}<div class="top"><div class="icon">{icon(it.get("icon"))}</div>'
                     f'<div class="label">{e(it.get("label"))}</div></div>'
                     f'<div class="main">{e(it.get("main"))}</div><div class="note">{e(it.get("note"))}</div></div>')
    return f'<div class="grid" style="grid-template-columns:repeat({n},1fr)">{"".join(cells)}</div>'


def panels(spec):
    items = spec["items"]
    out = []
    for i, it in enumerate(items, 1):
        photo = f'<img src="{html.escape(it["photo"], quote=True)}">' if it.get("photo") else ""
        rows = "".join(f'<div class="row">{icon(ic)}<div class="k">{e(k)}</div><div class="v">{e(v)}</div></div>'
                       for ic, k, v in it.get("rows", []))
        note = f'<div class="pnote">{e(it.get("note"))}</div>' if it.get("note") else ""
        out.append(f'<div class="panel"><div class="head"><div class="no">{i}</div><div class="title">{e(it.get("title"))}</div></div>'
                   f'{photo}<div class="rows">{rows}</div>{note}</div>')
    return f'<div class="panels" style="grid-template-columns:repeat({len(items)},1fr)">{"".join(out)}</div>'


def timeline(spec):
    items = spec["items"]
    evs = "".join(f'<div class="ev{" hot" if it.get("hot") else ""}"><div class="date">{e(it.get("date"))}</div><div class="dot"></div>'
                  f'<div class="title">{e(it.get("title"))}</div><div class="note">{e(it.get("note"))}</div></div>' for it in items)
    return f'<div class="tl" style="grid-template-columns:repeat({len(items)},1fr)">{evs}</div>'


def mark(value):
    v = str(value).strip()
    kind = {"O": "o", "△": "h", "X": "x"}.get(v.upper() if v.isascii() else v)
    return f'<span class="mark {kind}"></span>' if kind else e(v)


def compare(spec):
    head = "".join(f"<th>{e(c)}</th>" for c in [""] + spec["columns"])
    rows = "".join("<tr><td>" + e(it["name"]) + "</td>" + "".join(f"<td>{mark(c)}</td>" for c in it["cells"]) + "</tr>"
                   for it in spec["items"])
    used = {str(c).strip().upper() for it in spec["items"] for c in it["cells"]}
    names = spec.get("legend", {"O": "된다", "△": "일부만", "X": "안 된다"})
    legend = "".join(f'<span><span class="mark {k}"></span>{e(names.get(sym, ""))}</span>'
                     for sym, k in (("O", "o"), ("△", "h"), ("X", "x")) if sym in used)
    return f'<table class="cmp"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>' + (
        f'<div class="legend">{legend}</div>' if legend else "")


def pick(spec):
    rows = "".join(f'<div class="pk"><div class="if">{e(it.get("if"))}</div><div class="arrow">{icon("arrow-right", "ic")}</div>'
                   f'<div class="then">{e(it.get("then"))}' + (f'<small>{e(it.get("note"))}</small>' if it.get("note") else "")
                   + "</div></div>" for it in spec["items"])
    return f'<div class="pick">{rows}</div>'


def number(spec):
    b = spec["big"]
    stats = "".join(f'<div class="st"><div class="v">{e(it.get("value"))}</div><div class="l">{e(it.get("label"))}</div></div>'
                    for it in spec.get("items", []))
    return (f'<div class="num"><div class="big"><div class="v">{e(b.get("value"))}<span>{e(b.get("unit"))}</span></div>'
            f'<div class="l">{e(b.get("label"))}</div></div><div class="stats">{stats}</div></div>')


LAYOUTS = {"grid": grid, "panels": panels, "timeline": timeline, "compare": compare, "pick": pick, "number": number}


def page(spec):
    accent, tint = THEMES[spec.get("theme", "plain")]
    sub = f'<div class="sub">{e(spec.get("sub"))}</div>' if spec.get("sub") else ""
    return (f'<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="{FONT}"><style>{CSS}</style>'
            f'<body style="--a:{accent};--t:{tint}"><div class="slide">'
            f'<div class="kicker">{e(spec.get("kicker"))}</div><h1>{e(spec.get("title"))}</h1>{sub}'
            f'<div class="body">{LAYOUTS[spec["layout"]](spec)}</div>'
            f'<div class="foot"><span>{e(spec.get("foot"))}</span><b>memorily</b></div></div>'
            f'<script src="{ICONS}"></script><script>lucide.createIcons()</script></body>')


def shoot(doc, out):
    tmp = Path(tempfile.mkdtemp())
    src = tmp / "card.html"
    src.write_text(doc, encoding="utf-8")
    shot = tmp / "shot.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--user-data-dir={tmp / 'prof'}", "--window-size=1260,1800", "--virtual-time-budget=8000",
                    f"--screenshot={shot}", src.as_uri()], check=True, capture_output=True)
    im = Image.open(shot).convert("RGB").crop((0, 0, W, 1800))
    gray = im.convert("L")
    bottom = next(y for y in range(im.height - 1, 0, -1) if gray.crop((0, y, W, y + 1)).getextrema() not in ((0, 0), (255, 255)))
    im = im.crop((0, 0, W, max(MIN_H, bottom + 40)))
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path, help="설계 json (UTF-8)")
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    spec = json.loads(a.spec.read_text(encoding="utf-8"))
    shoot(page(spec), a.out)
    print(a.out)


if __name__ == "__main__":
    main()
