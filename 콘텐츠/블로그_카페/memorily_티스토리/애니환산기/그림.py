"""애니 작품 가공이미지 2장 (620 폭, 2026-10-21 사용자: 글 이미지는 620): 대표 + '어디까지 만화 내용일까' 막대.
python 그림.py <작품키> <색> "<막대 그림 아래 한 줄>"   예: python 그림.py bleach "#EA580C" "블리치는 366화에서 끝나요."
data/<작품키>.json 을 읽어 사진/<작품키>-cover.png · <작품키>-chart.png 를 만든다 (크롬 헤드리스 캡처 + PIL 자르기).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops

HERE = Path(__file__).parent
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
key, color, last_line = sys.argv[1:4]
w = json.load(open(HERE / "data" / f"{key}.json", encoding="utf-8"))
NM = w.get("short", w["name"])
UN = w.get("unit", "만화")  # 원작이 소설이면 data 의 "unit": "소설" (그림 글자만 바뀐다)  # 이름이 길면 그림에는 짧은 이름 (data 의 "short")
out = tempfile.mkdtemp()
DK, MID, LT, GR = "#1F2937", "#4B5563", "#9CA3AF", "#D9DCE1"
HEAD = ('<!doctype html><meta charset="utf-8"><link rel="stylesheet" '
        'href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">'
        '<style>body{margin:0;background:#fff}.f{font-family:Pretendard,"Malgun Gothic",sans-serif;color:%s;width:620px;'
        'box-sizing:border-box;background:#fff;position:relative}</style><body>' % DK)


def vol(ch):
    return max(i + 1 for i, v in enumerate(w["vols"]) if v <= ch)


def canon_range(eps):
    chs = [c for e in eps if e[2] for c in (e[0], e[1]) if c > 0]  # 음수 화(과거편)는 범위에서 뺀다
    return (min(chs), max(chs)) if chs else None


series = w["series"]
total = sum(len(s["eps"]) for s in series)

# 대표 620×325
bars = "".join(f'<div style="flex:{len(s["eps"])};height:10px;border-radius:5px;background:{color if i == 0 else DK}"></div>'
               for i, s in enumerate(series))
labels = "".join(f'<div style="flex:{len(s["eps"])};font-size:12px;color:#6B7280;white-space:nowrap;overflow:visible">{s["name"]} {len(s["eps"])}화</div>'
                 for s in series)
if len(series) == 1:  # 시리즈가 하나면 '만화 전체 중 애니가 따라온 만큼'
    r = canon_range(series[0]["eps"])
    pct = r[1] / w["last"] * 100
    bars = (f'<div style="flex:1;position:relative;height:10px;border-radius:5px;background:{GR};overflow:hidden">'
            f'<div style="position:absolute;left:0;top:0;bottom:0;width:{pct:.1f}%;background:{color}"></div></div>')
    labels = (f'<div style="flex:1;display:flex;justify-content:space-between;font-size:12px;color:#6B7280">'
              f'<span>애니 {len(series[0]["eps"])}화 = {UN} {r[1]}화까지</span><span>{UN} {w["last"]}화</span></div>')
cover = (f'<div class="f" style="height:325px;padding:44px 50px">'
         f'<div style="width:30px;height:4px;border-radius:2px;background:{color}"></div>'
         f'<div style="margin-top:18px;font-size:16px;font-weight:600;color:#6B7280">{NM} · 애니 ↔ {UN}</div>'
         f'<div style="margin-top:6px;font-size:{38 if len(NM) > 9 else 44}px;font-weight:800;letter-spacing:-1px">{NM} 회차정리</div>'
         f'<div style="margin-top:10px;font-size:18px;color:#374151">환산기 · 애니 오리지널 회차 · 명장면 몇 화</div>'
         f'<div style="position:absolute;left:50px;right:50px;bottom:40px"><div style="display:flex;gap:8px">{bars}</div>'
         f'<div style="display:flex;gap:8px;margin-top:8px">{labels}</div></div></div>')
open(f"{out}/{key}-cover.html", "w", encoding="utf-8").write(HEAD + cover)

# 어디까지 만화 내용일까
W = 520
rows = ""
for s in series:
    n = len(s["eps"])
    cw = W / n
    cells = "".join(f'<i style="position:absolute;top:0;bottom:0;left:{i * cw:.2f}px;width:{cw + 0.5:.2f}px;background:{color if e[2] else GR}"></i>'
                    for i, e in enumerate(s["eps"]))
    r = canon_range(s["eps"])
    right = f"{UN} {r[0]}~{r[1]}화 · {vol(r[0])}~{vol(r[1])}권" if r else ""
    rows += (f'<div style="margin-top:22px"><div style="display:flex;justify-content:space-between;align-items:baseline">'
             f'<b style="font-size:16px">{s["name"]}</b><span style="font-size:12px;color:#6B7280">{right}</span></div>'
             f'<div style="position:relative;height:28px;border-radius:6px;overflow:hidden;background:#eee;margin-top:8px;width:{W}px">{cells}</div>'
             f'<div style="display:flex;justify-content:space-between;margin-top:4px;font-size:11px;color:{LT};width:{W}px"><span>1화</span><span>{n}화</span></div></div>')
legend = (f'<div style="margin-top:8px;display:flex;gap:14px;font-size:12px;color:{MID}">'
          f'<span><i style="display:inline-block;width:10px;height:10px;border-radius:2px;background:{color};vertical-align:-1px"></i> {UN} 내용</span>'
          f'<span><i style="display:inline-block;width:10px;height:10px;border-radius:2px;background:{GR};vertical-align:-1px"></i> 애니 오리지널</span></div>')
chart = (f'<div class="f" style="padding:34px 50px 30px"><div style="font-size:21px;font-weight:800;letter-spacing:-0.5px">'
         f'{NM} 애니, 어디까지 {UN} 내용일까</div>{legend}{rows}'
         f'<div style="margin-top:20px;font-size:12px;color:#6B7280">{last_line}</div></div>')
open(f"{out}/{key}-chart.html", "w", encoding="utf-8").write(HEAD + chart)


def capture(kind):
    png = Path(out) / f"{key}-{kind}.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1", f"--user-data-dir={out}/prof",
                    "--window-size=680,1000", "--virtual-time-budget=6000", f"--screenshot={png}",
                    (Path(out) / f"{key}-{kind}.html").as_uri()], capture_output=True, timeout=120)
    im = Image.open(png).convert("RGB")
    im = im.crop((0, 0, 620, im.height))
    if kind == "cover":
        im = im.crop((0, 0, 620, 325))
    else:
        im = im.crop((0, 0, 620, ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()[3] + 30))
    im.save(HERE / "사진" / f"{key}-{kind}.png", optimize=True)
    print(key, kind, im.size)


capture("cover")
capture("chart")
