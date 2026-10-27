"""여행 글 맨 위 위치 지도 (2026-10-27 사용자: "나는 사실 어딘지도 몰라 너가 쓰는 지역들이" → 글 첫머리에 여기가 어디인지).
python 위치지도.py <사이트> <나라 ISO3 | 시도 코드> <도시> <위도> <경도> <저장할 png> [--span 경도폭] [--near 이름:위도:경도,…] [--title …] [--sub …]
  밤밤: 한국어 · 흰 바탕 회색 땅 · 빨강 한 가지. 두 칸 — 왼쪽 서울에서 그 도시까지(점선), 오른쪽 그 나라 가까이.
  워드프레스: 영어 · 글모양.css 여행(테라코타·모래) · 제목은 세리프. 넓은 지도 한 장 + 구석에 세계 지도, 런던·뉴욕·시드니에서 거리.
  black_lukey: 국내 지역 놀거리 (네이버). 두 번째 값은 시도 코드 (KR-48 경남 · KR-42 강원 …, ISO 3166-2). 정보 카드 '가 볼 곳'의 초록.
    두 칸 — 왼쪽 우리나라 전체에 그 시도 칠하기 · 서울, 오른쪽 그 도시 가까이 (시도 경계 · 이웃 도시). 제목 '경남 통영'.
  워드프레스 + 시도 코드 (Korea Travel): 영어 · 여행 테라코타. 그 도시 가까이 넓은 지도 한 장 + 구석에 우리나라 작은 지도,
    서울·부산에서 거리.
  --span: 가까운 지도의 가로 폭(경도). 홍콩처럼 나라가 작으면 3 정도로 넓힌다. 없으면 나라 크기에 맞춘다.
  --near: 가까운 지도에 회색 점으로 찍을 이웃 도시 (예: '잘츠부르크:47.80:13.04,프라하:50.08:14.44').
지도: Natural Earth 1:10m·1:110m 나라·시도 경계 (퍼블릭 도메인). 처음 쓸 때 workspace/.routine/ne/ 로 받는다.
만드는 법은 다른 가공이미지와 같다: HTML(SVG) → 크롬 헤드리스 캡처 → PIL 로 1200px·내용 높이만 자른다.
"""
import argparse
import html
import json
import math
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
NE_DIR = ROOT / "workspace" / ".routine" / "ne"
NE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/{}.geojson"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
FONT = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
SEOUL = (37.5665, 126.9780)
FROM_KR = (("Seoul", 37.5665, 126.9780), ("Busan", 35.1796, 129.0756))
FROM_EN = (("London", 51.5072, -0.1276), ("New York", 40.7128, -74.0060), ("Sydney", -33.8688, 151.2093))
SHORT_KO = {"CHN": "중국", "PRK": "북한", "KOR": "한국", "TWN": "대만", "USA": "미국", "GBR": "영국", "CZE": "체코",
            "AUS": "호주", "ARE": "아랍에미리트", "ZAF": "남아공", "BIH": "보스니아", "COD": "콩고", "COG": "콩고"}
CONTINENT_KO = {"Europe": "유럽", "Asia": "아시아", "Africa": "아프리카", "Oceania": "오세아니아",
                "North America": "북아메리카", "South America": "남아메리카"}

# 사이트별 색 (밤밤: 변환그림 56 '7일권 손익'의 빨강·회색 / 워드프레스: 글모양.css .jb-travel)
LOOKS = {
    "밤밤": {"ink": "#222222", "ink2": "#6b7280", "sea": "#f3f5f7", "land": "#dfe3e7", "home": "#c3c8ce",
            "border": "#ffffff", "accent": "#c0392b", "mark": "#222222", "label": "#8a9097",
            "title_font": "Pretendard", "lang": "ko"},
    "워드프레스": {"ink": "#2e2723", "ink2": "#5a4f48", "sea": "#f7f1e8", "land": "#e9dccb", "home": "#e9dccb",
              "border": "#ffffff", "accent": "#b4532a", "mark": "#7a3a1f", "label": "#9a8878",
              "title_font": 'Georgia, "Iowan Old Style", "Times New Roman", serif', "lang": "en"},
    # black_lukey: apps/writing/render.CARD_KINDS '장소' (#1f6f5c · 연한 바탕 #eef6f2)
    "black_lukey": {"ink": "#222222", "ink2": "#6b7280", "sea": "#f3f5f7", "land": "#dfe3e7", "home": "#eceef0",
                    "border": "#ffffff", "accent": "#b5dbc9", "glow": "#1f6f5c", "mark": "#1f6f5c", "label": "#8a9097",
                    "title_font": "Pretendard", "lang": "ko"},
}
# Natural Earth 의 옛 이름 → 지금 이름 (2023 강원특별자치도 · 2024 전북특별자치도)
PROV_NAME = {"강원도": "강원특별자치도", "전라북도": "전북특별자치도"}


def load(name):
    path = NE_DIR / f"{name}.geojson"
    if not path.exists():
        NE_DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(NE_URL.format(name), path)
    return json.load(open(path, encoding="utf-8"))["features"]


def km(a, b):
    (la1, lo1), (la2, lo2) = [(math.radians(p[0]), math.radians(p[1])) for p in (a, b)]
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def great_circle(a, b, n=64):
    """두 점 사이 대권 경로 (위도, 경도) 점들."""
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    d = 2 * math.asin(math.sqrt(math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2))
    pts = []
    for i in range(n + 1):
        f = i / n
        A, B = math.sin((1 - f) * d) / math.sin(d), math.sin(f * d) / math.sin(d)
        x = A * math.cos(la1) * math.cos(lo1) + B * math.cos(la2) * math.cos(lo2)
        y = A * math.cos(la1) * math.sin(lo1) + B * math.cos(la2) * math.sin(lo2)
        z = A * math.sin(la1) + B * math.sin(la2)
        pts.append((math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))))
    return pts


class View:
    """가까운 범위용 등장방형 (가로를 가운데 위도의 cos 로 줄인다). w·h 픽셀 칸에 lat/lon 범위를 맞춘다."""

    def __init__(self, lats, lons, w, h, pad=0.12, plain=False):
        self.w, self.h = w, h
        self.lat0 = (max(lats) + min(lats)) / 2
        self.lon0 = (max(lons) + min(lons)) / 2
        self.c = 1.0 if plain else math.cos(math.radians(self.lat0))
        dx = (max(lons) - min(lons)) * self.c or 1e-6
        dy = (max(lats) - min(lats)) or 1e-6
        self.k = min(w * (1 - 2 * pad) / dx, h * (1 - 2 * pad) / dy)

    def xy(self, lat, lon):
        return self.w / 2 + (lon - self.lon0) * self.c * self.k, self.h / 2 - (lat - self.lat0) * self.k

    def latlon(self, x, y):
        return self.lat0 - (y - self.h / 2) / self.k, self.lon0 + (x - self.w / 2) / (self.c * self.k)

    def latlon_box(self):
        dlon = self.w / 2 / (self.c * self.k)
        dlat = self.h / 2 / self.k
        return self.lat0 - dlat, self.lat0 + dlat, self.lon0 - dlon, self.lon0 + dlon


def rings(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [r for poly in geom["coordinates"] for r in poly]


def outer_rings(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    return [poly[0] for poly in geom["coordinates"]]


def path_d(geom, view, margin=40):
    out = []
    for ring in rings(geom):
        pts = [view.xy(lat, lon) for lon, lat in ring]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        if max(xs) < -margin or min(xs) > view.w + margin or max(ys) < -margin or min(ys) > view.h + margin:
            continue
        keep, last = [], None
        for p in pts:  # 0.7px 안쪽으로 붙은 점은 뺀다 (10m 데이터를 그대로 넣으면 SVG 가 너무 커진다)
            if last is None or abs(p[0] - last[0]) + abs(p[1] - last[1]) > 0.7:
                keep.append(p)
                last = p
        if len(keep) >= 3:
            out.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in keep) + "Z")
    return "".join(out)


def proj_bbox(geom, view):
    xs, ys = [], []
    for ring in outer_rings(geom):
        for lon, lat in ring:
            x, y = view.xy(lat, lon)
            xs.append(x)
            ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def main_bbox(geom):
    """나라의 가장 큰 덩어리 범위 (해외 영토·섬 때문에 지도가 너무 넓어지지 않게)."""
    best = max(outer_rings(geom), key=lambda r: (max(p[0] for p in r) - min(p[0] for p in r)) * (max(p[1] for p in r) - min(p[1] for p in r)))
    lons, lats = [p[0] for p in best], [p[1] for p in best]
    return min(lats), max(lats), min(lons), max(lons)


def inside(geom, lat, lon):
    """점이 나라 안인가 (짝홀 규칙). 나라 안 이름은 흰 글씨로 쓴다."""
    hit = False
    for ring in rings(geom):
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
            if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                hit = not hit
    return hit


def text_w(s, size):
    return sum(size * (0.95 if ord(ch) > 0x2000 else 0.56) for ch in s)


class Labels:
    """겹치지 않게 이름을 놓는다. 먼저 놓은 것이 이긴다."""

    def __init__(self, w, h, on_accent=None):
        self.boxes, self.w, self.h, self.svg = [], w, h, []
        self.on_accent = on_accent  # (x, y) 가 칠한 나라 위인가 — 그 위 이름은 흰 글씨 · 빨강 테두리

    def free(self, box):
        x0, y0, x1, y1 = box
        if x0 < 6 or y0 < 6 or x1 > self.w - 6 or y1 > self.h - 6:
            return False
        return not any(x0 < b[2] and x1 > b[0] and y0 < b[3] and y1 > b[1] for b in self.boxes)

    def block(self, box):
        self.boxes.append(box)

    def put(self, text, x, y, size, color, weight=500, anchor="middle", halo="#ffffff", force=False):
        w = text_w(text, size)
        x0 = x - w / 2 if anchor == "middle" else (x if anchor == "start" else x - w)
        box = (x0 - 4, y - size * 0.85, x0 + w + 4, y + size * 0.3)
        if not force and not self.free(box):
            return False
        self.boxes.append(box)
        self.svg.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{color}" '
                        f'text-anchor="{anchor}" stroke="{halo}" stroke-width="{max(3, size // 5)}" stroke-linejoin="round" '
                        f'paint-order="stroke">{html.escape(text)}</text>')
        return True

    def city(self, text, x, y, size, color, weight, r, accent="#ffffff"):
        """점 옆 이름: 오른쪽 → 왼쪽 → 위 → 아래 순서로 빈자리. 점은 block 으로 미리 막아 둔다 (반지름 r)."""
        w, g = text_w(text, size), r + 8
        spots = [("start", x + g, y + size * 0.35), ("end", x - g, y + size * 0.35),
                 ("middle", x, y - g), ("middle", x, y + g + size * 0.7)]
        for n, (anchor, tx, ty) in enumerate(spots + spots[:1]):
            x0 = tx - w / 2 if anchor == "middle" else (tx if anchor == "start" else tx - w)
            if n == len(spots) or self.free((x0 - 4, ty - size * 0.85, x0 + w + 4, ty + size * 0.3)):
                on = self.on_accent and self.on_accent(x0 + w / 2, ty - size * 0.3)
                return self.put(text, tx, ty, size, "#ffffff" if on else color, weight, anchor,
                                accent if on else "#ffffff", force=True)


def map_svg(feats, view, look, iso, home=False):
    """땅 · 그 나라 칠하기 · 이웃 나라 이름. (svg 조각, Labels) 를 돌려준다."""
    parts, lab = [], Labels(view.w, view.h)
    for f in feats:
        d = path_d(f["geometry"], view)
        if not d:
            continue
        a3 = f["properties"]["ADM0_A3"]
        fill = look["accent"] if a3 == iso else (look["home"] if home and a3 == "KOR" else look["land"])
        parts.append(f'<path d="{d}" fill="{fill}" stroke="{look["border"]}" stroke-width="1.2" stroke-linejoin="round" fill-rule="evenodd"/>')
    return parts, lab


def country_labels(feats, view, lab, look, iso, name_key, size, label_min, skip=(), most=99):
    ranked = sorted(feats, key=lambda f: (f["properties"].get("LABELRANK") or 9, -(f["properties"].get("POP_EST") or 0)))
    for f in ranked:
        p = f["properties"]
        if p["ADM0_A3"] == iso or p["ADM0_A3"] in skip:
            continue
        x, y = view.xy(p["LABEL_Y"], p["LABEL_X"])
        if not (0 < x < view.w and 0 < y < view.h):
            continue
        x0, y0, x1, y1 = proj_bbox(f["geometry"], view)
        if min(x1, view.w) - max(x0, 0) < label_min or min(y1, view.h) - max(y0, 0) < size * 1.4:
            continue
        name = (SHORT_KO.get(p["ADM0_A3"]) if name_key == "NAME_KO" else None) or p.get(name_key) or p["NAME"]
        if len(name) > (7 if name_key == "NAME_KO" else 16):
            continue
        most -= lab.put(name, x, y + size * 0.35, size, look["label"], 600)
        if most <= 0:
            break


def panel(inner, w, h, look, radius=14):
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
            f'style="display:block;border-radius:{radius}px;background:{look["sea"]}">'
            f'<defs><clipPath id="c{w}{h}"><rect width="{w}" height="{h}" rx="{radius}"/></clipPath></defs>'
            f'<g clip-path="url(#c{w}{h})">{inner}</g></svg>')


def marker(x, y, look, r=9):
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r + 5}" fill="{look.get("glow", look["accent"])}" fill-opacity="0.18"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#ffffff" stroke="{look["mark"]}" stroke-width="4"/>')


def dot(x, y, color, r=5, ring="#ffffff"):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" stroke="{ring}" stroke-width="2"/>'


def near_list(text):
    out = []
    for item in filter(None, (s.strip() for s in (text or "").split(","))):
        name, lat, lon = item.rsplit(":", 2)
        out.append((name, float(lat), float(lon)))
    return out


def closeup_view(feat, lat, lon, w, h, span, grow):
    if span:
        dlat = span * (h / w) / math.cos(math.radians(lat))
        return View([lat - dlat / 2, lat + dlat / 2], [lon - span / 2, lon + span / 2], w, h, pad=0)
    la0, la1, lo0, lo1 = main_bbox(feat["geometry"])
    la0, la1, lo0, lo1 = min(la0, lat), max(la1, lat), min(lo0, lon), max(lo1, lon)
    cl, co = (la0 + la1) / 2, (lo0 + lo1) / 2
    return View([cl - (la1 - la0) * grow / 2, cl + (la1 - la0) * grow / 2],
                [co - (lo1 - lo0) * grow / 2, co + (lo1 - lo0) * grow / 2], w, h, pad=0)


def closeup(feats, feat, a, look, w, h, grow, name_key, size):
    view = closeup_view(feat, a.lat, a.lon, w, h, a.span, grow)
    parts, lab = map_svg(feats, view, look, a.iso)
    lab.on_accent = lambda px, py: inside(feat["geometry"], *view.latlon(px, py))
    x, y = view.xy(a.lat, a.lon)
    lab.block((x - 15, y - 15, x + 15, y + 15))
    near = []
    for name, la, lo in near_list(a.near):
        nx, ny = view.xy(la, lo)
        if 8 < nx < w - 8 and 8 < ny < h - 8:
            lab.block((nx - 7, ny - 7, nx + 7, ny + 7))
            near.append((name, nx, ny, inside(feat["geometry"], la, lo)))
    lab.city(a.city, x, y, size + 6, look["ink"], 800, 13, look["accent"])
    for name, nx, ny, _ in near:
        lab.city(name, nx, ny, size - 2, look["ink2"], 600, 6, look["accent"])
    country_labels(feats, view, lab, look, a.iso, name_key, size, 70)
    dots = "".join(dot(nx, ny, "#ffffff" if inn else look["ink2"], 5, look["accent"] if inn else "#ffffff") for _, nx, ny, inn in near)
    body = "".join(parts) + dots + marker(x, y, look) + "".join(lab.svg)
    return view, body


def bambam(a, feats, feat):
    look = LOOKS["밤밤"]
    ko = feat["properties"]["NAME_KO"] or feat["properties"]["NAME"]
    dist = km(SEOUL, (a.lat, a.lon))
    title = a.title or (a.city if a.city == ko else f"{ko} {a.city}")
    cont = CONTINENT_KO.get(feat["properties"]["CONTINENT"], "")
    sub = a.sub or " · ".join(s for s in (cont, f"서울에서 직선 약 {round(dist, -1):,.0f}km") if s)
    W, H = 550, 440
    # 왼쪽: 서울에서 그 도시까지
    arc = great_circle(SEOUL, (a.lat, a.lon))
    lv = View([p[0] for p in arc], [p[1] for p in arc], W, H, pad=0.16)
    parts, lab = map_svg(feats, lv, look, a.iso, home=True)
    sx, sy = lv.xy(*SEOUL)
    cx, cy = lv.xy(a.lat, a.lon)
    line = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in (lv.xy(*p) for p in arc))
    for la, lo in arc[8:-8:6]:  # 점선 위에는 이름을 놓지 않는다
        px, py = lv.xy(la, lo)
        lab.block((px - 4, py - 4, px + 4, py + 4))
    lab.block((sx - 9, sy - 9, sx + 9, sy + 9))
    lab.block((cx - 15, cy - 15, cx + 15, cy + 15))
    lab.city(a.city, cx, cy, 26, look["ink"], 800, 13)
    lab.city("서울", sx, sy, 22, look["ink"], 700, 7)
    country_labels(feats, lv, lab, look, a.iso, "NAME_KO", 19, 50, skip=("KOR",), most=5)
    left = ("".join(parts) + f'<path d="{line}" fill="none" stroke="{look["ink"]}" stroke-width="2.5" stroke-dasharray="7 7" stroke-linecap="round"/>'
            + dot(sx, sy, look["ink"], 7) + marker(cx, cy, look) + "".join(lab.svg))
    # 오른쪽: 그 나라 가까이
    _, right = closeup(feats, feat, a, look, W, H, 1.7, "NAME_KO", 20)
    body = (f'<div style="padding:44px 40px 40px;width:1200px;box-sizing:border-box;background:#fff;color:{look["ink"]};'
            f'font-family:Pretendard,\'Malgun Gothic\',sans-serif">'
            f'<div style="font-size:44px;font-weight:800;letter-spacing:-1px;line-height:1.25">{html.escape(title)}</div>'
            f'<div style="margin-top:10px;font-size:23px;color:{look["ink2"]}">{html.escape(sub)}</div>'
            f'<div style="margin-top:30px;display:flex;gap:20px">{panel(left, W, H, look)}{panel(right, W, H, look)}</div>'
            f'<div style="margin-top:14px;font-size:16px;color:#9aa0a6">지도: Natural Earth</div></div>')
    return body


def wordpress(a, feats, feat, world):
    look = LOOKS["워드프레스"]
    en = feat["properties"]["NAME_EN"] or feat["properties"]["NAME"]
    title = a.title or f"{a.city}, {en}"
    region = feat["properties"].get("SUBREGION") or feat["properties"]["CONTINENT"]
    sub = a.sub or " · ".join([region] + [f"{round(km((la, lo), (a.lat, a.lon)), -1):,.0f} km from {n}" for n, la, lo in FROM_EN])
    W, H = 1120, 600
    view, body = closeup(feats, feat, a, look, W, H, 2.4, "NAME_EN", 19)
    # 구석 세계 지도: 지금 보는 범위를 네모로
    iw, ih = 300, 128
    wv = View([-58, 80], [-180, 180], iw, ih, pad=0, plain=True)
    wparts = []
    for f in world:
        d = path_d(f["geometry"], wv, margin=0)
        if d:
            fill = look["accent"] if f["properties"]["ADM0_A3"] == a.iso else look["land"]
            wparts.append(f'<path d="{d}" fill="{fill}"/>')
    la0, la1, lo0, lo1 = view.latlon_box()
    (rx0, ry0), (rx1, ry1) = wv.xy(la1, lo0), wv.xy(la0, lo1)
    wx, wy = wv.xy(a.lat, a.lon)
    inset = (f'<g transform="translate({W - iw - 18},{H - ih - 18})"><rect x="-8" y="-8" width="{iw + 16}" height="{ih + 16}" rx="10" '
             f'fill="#ffffff" stroke="#eadccd"/>{"".join(wparts)}'
             f'<rect x="{rx0:.1f}" y="{ry0:.1f}" width="{max(rx1 - rx0, 6):.1f}" height="{max(ry1 - ry0, 6):.1f}" fill="none" '
             f'stroke="{look["mark"]}" stroke-width="2"/><circle cx="{wx:.1f}" cy="{wy:.1f}" r="3.5" fill="{look["mark"]}"/></g>')
    serif = look["title_font"]
    return (f'<div style="padding:44px 40px 40px;width:1200px;box-sizing:border-box;background:#fff;color:{look["ink"]};'
            f'font-family:Pretendard,\'Segoe UI\',sans-serif">'
            f'<div style="font-family:{html.escape(serif)};font-size:46px;font-weight:700;line-height:1.2">{html.escape(title)}</div>'
            f'<div style="margin-top:12px;font-size:22px;color:{look["ink2"]}">{html.escape(sub)}</div>'
            f'<div style="margin-top:28px">{panel(body + inset, W, H, look)}</div>'
            f'<div style="margin-top:14px;font-size:16px;color:#a89888">Map data: Natural Earth</div></div>')


def prov_short(name):
    """경상남도 → 경남, 서울특별시 → 서울, 강원특별자치도 → 강원."""
    for tail in ("특별자치시", "특별자치도", "특별시", "광역시"):
        if name.endswith(tail):
            return name[:-len(tail)]
    if name[:2] in ("경상", "전라", "충청") and len(name) == 4:
        return name[0] + name[2]
    return name[:-1] if name.endswith("도") else name


def korea_land(view, look, countries, kor, prov, margin=40):
    """이웃 나라 · 시도 (그 시도만 칠한다)."""
    parts = []
    for f in countries:
        if f["properties"]["ADM0_A3"] != "KOR" and (d := path_d(f["geometry"], view, margin)):
            parts.append(f'<path d="{d}" fill="{look["home"]}" stroke="{look["border"]}" stroke-width="1.2" fill-rule="evenodd"/>')
    for f in kor:
        if d := path_d(f["geometry"], view, margin):
            fill = look["accent"] if f is prov else look["land"]
            parts.append(f'<path d="{d}" fill="{fill}" stroke="{look["border"]}" stroke-width="1.4" stroke-linejoin="round" fill-rule="evenodd"/>')
    return parts


def korea(a, countries, kor, prov):
    """국내 지역 놀거리: 왼쪽 우리나라 전체 · 오른쪽 그 도시 가까이. 칠하는 단위는 시도."""
    look = LOOKS["black_lukey"]
    pname = PROV_NAME.get(prov["properties"]["name_ko"], prov["properties"]["name_ko"])
    short = prov_short(pname)
    title = a.title or (a.city if a.city == short else f"{short} {a.city}")
    sub = a.sub or f"{pname} · 서울에서 직선 약 {round(km(SEOUL, (a.lat, a.lon)), -1):,.0f}km"
    W, H = 550, 440

    def land(view):
        return korea_land(view, look, countries, kor, prov)

    def prov_labels(view, lab, size, skip_home):
        for f in kor:
            p = f["properties"]
            if f is prov and skip_home:
                continue
            x, y = view.xy(p["latitude"], p["longitude"])
            name = prov_short(PROV_NAME.get(p["name_ko"], p["name_ko"]))
            if 0 < x < view.w and 0 < y < view.h and len(name) <= 3:
                color, weight = (look["mark"], 800) if f is prov else (look["label"], 600)
                lab.put(name, x, y + size * 0.35, size, color, weight)

    # 왼쪽: 우리나라 전체 (울릉도까지)
    lv = View([33.05, 38.7], [124.9, 131.0], W, H, pad=0.03)
    lab = Labels(W, H)
    cx, cy = lv.xy(a.lat, a.lon)
    lab.block((cx - 15, cy - 15, cx + 15, cy + 15))
    lab.city(a.city, cx, cy, 26, look["ink"], 800, 13)
    seoul = km(SEOUL, (a.lat, a.lon)) > 30
    if seoul:
        sx, sy = lv.xy(*SEOUL)
        lab.block((sx - 9, sy - 9, sx + 9, sy + 9))
        lab.city("서울", sx, sy, 22, look["ink"], 700, 7)
    lx, ly = lv.xy(prov["properties"]["latitude"], prov["properties"]["longitude"])
    lab.put(short, lx, ly + 8, 22, look["mark"], 800)
    left = "".join(land(lv)) + (dot(sx, sy, look["ink"], 7) if seoul else "") + marker(cx, cy, look) + "".join(lab.svg)
    # 오른쪽: 그 도시 가까이
    span = a.span or 1.5
    dlat = span * (H / W) / math.cos(math.radians(a.lat))
    rv = View([a.lat - dlat / 2, a.lat + dlat / 2], [a.lon - span / 2, a.lon + span / 2], W, H, pad=0)
    lab = Labels(W, H)
    x, y = rv.xy(a.lat, a.lon)
    lab.block((x - 15, y - 15, x + 15, y + 15))
    near = []
    for name, la, lo in near_list(a.near):
        nx, ny = rv.xy(la, lo)
        if 8 < nx < W - 8 and 8 < ny < H - 8:
            lab.block((nx - 7, ny - 7, nx + 7, ny + 7))
            near.append((name, nx, ny))
    lab.city(a.city, x, y, 28, look["ink"], 800, 13)
    for name, nx, ny in near:
        lab.city(name, nx, ny, 20, look["ink2"], 600, 6)
    prov_labels(rv, lab, 20, skip_home=False)
    right = "".join(land(rv)) + "".join(dot(nx, ny, look["ink2"]) for _, nx, ny in near) + marker(x, y, look) + "".join(lab.svg)
    return (f'<div style="padding:44px 40px 40px;width:1200px;box-sizing:border-box;background:#fff;color:{look["ink"]};'
            f'font-family:Pretendard,sans-serif">'
            f'<div style="font-size:44px;font-weight:800;letter-spacing:-1px;line-height:1.25">{html.escape(title)}</div>'
            f'<div style="margin-top:10px;font-size:23px;color:{look["ink2"]}">{html.escape(sub)}</div>'
            f'<div style="margin-top:30px;display:flex;gap:20px">{panel(left, W, H, look)}{panel(right, W, H, look)}</div>'
            f'<div style="margin-top:14px;font-size:16px;color:#9aa0a6">지도: Natural Earth</div></div>')


def wp_korea(a, countries, kor, prov):
    """워드프레스 Korea Travel: 그 도시 가까이 넓은 지도 + 구석에 우리나라 작은 지도 (World Travel 과 같은 짜임)."""
    look = LOOKS["워드프레스"]
    pen = prov["properties"]["name_en"]
    title = a.title or f"{a.city}, South Korea"
    froms = [f"{round(d, -1):,.0f} km from {n}" for n, la, lo in FROM_KR if (d := km((la, lo), (a.lat, a.lon))) > 30]
    sub = a.sub or " · ".join(([] if a.city.lower() in pen.lower() else [pen]) + froms)
    W, H = 1120, 600
    span = a.span or 2.2
    dlat = span * (H / W) / math.cos(math.radians(a.lat))
    view = View([a.lat - dlat / 2, a.lat + dlat / 2], [a.lon - span / 2, a.lon + span / 2], W, H, pad=0)
    lab = Labels(W, H, on_accent=lambda px, py: inside(prov["geometry"], *view.latlon(px, py)))
    x, y = view.xy(a.lat, a.lon)
    lab.block((x - 15, y - 15, x + 15, y + 15))
    near = []
    for name, la, lo in near_list(a.near):
        nx, ny = view.xy(la, lo)
        if 8 < nx < W - 8 and 8 < ny < H - 8:
            lab.block((nx - 7, ny - 7, nx + 7, ny + 7))
            near.append((name, nx, ny, inside(prov["geometry"], la, lo)))
    lab.block((W - 230, H - 270, W, H))  # 구석 지도 자리
    lab.city(a.city, x, y, 27, look["ink"], 800, 13, look["accent"])
    for name, nx, ny, _ in near:
        lab.city(name, nx, ny, 19, look["ink2"], 600, 6, look["accent"])
    for f in kor:
        p = f["properties"]
        px, py = view.xy(p["latitude"], p["longitude"])
        if f is not prov and 0 < px < W and 0 < py < H and p["name_en"] not in {n for n, *_ in near}:  # 울산시 점과 울산 이름이 겹치지 않게
            lab.put(p["name_en"], px, py + 7, 19, look["label"], 600)
    dots = "".join(dot(nx, ny, "#ffffff" if inn else look["ink2"], 5, look["accent"] if inn else "#ffffff") for _, nx, ny, inn in near)
    # 구석: 우리나라 전체에 그 시도 · 지금 보는 범위 네모
    iw, ih = 190, 230
    iv = View([33.05, 38.65], [124.6, 130.7], iw, ih, pad=0.03)
    ipart = "".join(korea_land(iv, look, countries, kor, prov, margin=0)).replace('stroke-width="1.4"', 'stroke-width="0.6"').replace('stroke-width="1.2"', 'stroke-width="0.6"')
    la0, la1, lo0, lo1 = view.latlon_box()
    (rx0, ry0), (rx1, ry1) = iv.xy(la1, lo0), iv.xy(la0, lo1)
    inset = (f'<g transform="translate({W - iw - 18},{H - ih - 18})"><rect x="-8" y="-8" width="{iw + 16}" height="{ih + 16}" rx="10" '
             f'fill="{look["sea"]}" stroke="#eadccd"/><svg width="{iw}" height="{ih}" overflow="hidden">{ipart}'
             f'<rect x="{rx0:.1f}" y="{ry0:.1f}" width="{max(rx1 - rx0, 6):.1f}" height="{max(ry1 - ry0, 6):.1f}" fill="none" '
             f'stroke="{look["mark"]}" stroke-width="2"/></svg></g>')
    body = "".join(korea_land(view, look, countries, kor, prov)) + dots + marker(x, y, look) + "".join(lab.svg) + inset
    serif = look["title_font"]
    return (f'<div style="padding:44px 40px 40px;width:1200px;box-sizing:border-box;background:#fff;color:{look["ink"]};'
            f'font-family:Pretendard,sans-serif">'
            f'<div style="font-family:{html.escape(serif)};font-size:46px;font-weight:700;line-height:1.2">{html.escape(title)}</div>'
            f'<div style="margin-top:12px;font-size:22px;color:{look["ink2"]}">{html.escape(sub)}</div>'
            f'<div style="margin-top:28px">{panel(body, W, H, look)}</div>'
            f'<div style="margin-top:14px;font-size:16px;color:#a89888">Map data: Natural Earth</div></div>')


def shoot(body, out):
    tmp = Path(tempfile.mkdtemp())
    page = tmp / "map.html"
    page.write_text(f'<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="{FONT}">'
                    f'<style>body{{margin:0;background:#fff}}</style><body>{body}</body>', encoding="utf-8")
    shot = tmp / "shot.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={tmp / 'prof'}", "--window-size=1260,1400", "--virtual-time-budget=6000",
                    f"--screenshot={shot}", page.as_uri()], check=True, capture_output=True)
    im = Image.open(shot).convert("RGB").crop((0, 0, 1200, 1400))
    gray = im.convert("L")
    bottom = next(y for y in range(im.height - 1, 0, -1) if gray.crop((0, y, 1200, y + 1)).getextrema() not in ((0, 0), (255, 255)))
    im = im.crop((0, 0, 1200, min(im.height, bottom + 40)))
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", choices=sorted(LOOKS))
    ap.add_argument("iso", help="나라 ISO3 (Natural Earth ADM0_A3, 예: AUT · HKG · ITA) · black_lukey 는 시도 코드 (KR-48)")
    ap.add_argument("city")
    ap.add_argument("lat", type=float)
    ap.add_argument("lon", type=float)
    ap.add_argument("out", type=Path)
    ap.add_argument("--span", type=float, default=0)
    ap.add_argument("--near", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--sub", default="")
    a = ap.parse_args()
    feats = load("ne_10m_admin_0_countries")
    if a.iso.startswith("KR-"):  # 국내: 시도 코드 (black_lukey 지역 놀거리 · 워드프레스 Korea Travel)
        kor = [f for f in load("ne_10m_admin_1_states_provinces") if f["properties"]["adm0_a3"] == "KOR"]
        prov = next((f for f in kor if f["properties"]["iso_3166_2"] == a.iso), None)
        if prov is None:
            raise SystemExit(f"{a.iso}: 시도 코드가 아니다 (예: KR-48 경남)")
        if a.site == "밤밤":
            raise SystemExit("밤밤은 해외만 (국내는 black_lukey · 워드프레스)")
        shoot((korea if a.site == "black_lukey" else wp_korea)(a, feats, kor, prov), a.out)
        print(a.out)
        return
    feat = next((f for f in feats if f["properties"]["ADM0_A3"] == a.iso), None)
    if feat is None:
        raise SystemExit(f"{a.iso}: Natural Earth 에 없는 나라 코드")
    body = bambam(a, feats, feat) if a.site == "밤밤" else wordpress(a, feats, feat, load("ne_110m_admin_0_countries"))
    shoot(body, a.out)
    print(a.out)


if __name__ == "__main__":
    main()
