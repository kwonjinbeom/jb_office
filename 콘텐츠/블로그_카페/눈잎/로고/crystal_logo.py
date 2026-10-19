"""눈 결정으로 이루어진 네잎클로버 로고 SVG 만들기 (2판).

잎 = 하트 곡선. 가장자리를 따라 결정을 촘촘히 놓아 잎 모양이 또렷하게 보이게 하고, 안쪽은 듬성듬성 채운다.
잎 뒤에는 옅은 잎 실루엣. 잎 네 장은 대각선(45°) 배치, 가운데에서 조금씩 띄워 잎 사이가 갈라져 보이게 한다.
"""
import math
import random
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
C = 256.0
K = 5.0      # 하트 크기
GAP = 12.0   # 잎을 가운데서 띄우는 거리


def heart_pts(n=240):
    """위로 선 잎 하나의 외곽 (끝이 가운데 쪽). 화면 좌표."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((C + K * x, C - GAP - K * (y + 17)))
    return pts


def inside(px, py, poly):
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def dist_edge(px, py, poly):
    return min(math.hypot(px - x, py - y) for x, y in poly)


def rot(x, y, deg):
    a = math.radians(deg)
    dx, dy = x - C, y - C
    return C + dx * math.cos(a) - dy * math.sin(a), C + dx * math.sin(a) + dy * math.cos(a)


def flake(x, y, r, angle, branches=True):
    parts = []
    for k in range(6):
        a = math.radians(angle + k * 60)
        parts.append(f"M{x:.1f} {y:.1f}L{x + r * math.cos(a):.1f} {y + r * math.sin(a):.1f}")
        if branches and r >= 6:
            for t, bl in ((0.55, 0.38), (0.82, 0.24)):
                bx, by = x + r * t * math.cos(a), y + r * t * math.sin(a)
                for s in (-1, 1):
                    b = a + s * math.radians(55)
                    parts.append(f"M{bx:.1f} {by:.1f}L{bx + r * bl * math.cos(b):.1f} {by + r * bl * math.sin(b):.1f}")
    return "".join(parts)


def leaf_flakes(edge_step, edge_size, in_step, in_size, seed, branches):
    """잎 하나(위로 선 것)의 결정 목록 [(x, y, r, angle)]"""
    rnd = random.Random(seed)
    poly = heart_pts()
    out = []
    # 가장자리: 곡선 길이를 따라 일정 간격
    acc, last = 0.0, poly[0]
    out.append((*poly[0], edge_size, rnd.uniform(0, 60)))
    for p in poly[1:]:
        acc += math.hypot(p[0] - last[0], p[1] - last[1])
        last = p
        if acc >= edge_step:
            acc = 0.0
            out.append((p[0], p[1], edge_size * (1 + rnd.uniform(-0.12, 0.12)), rnd.uniform(0, 60)))
    # 안쪽: 육각 격자, 가장자리에서 떨어진 곳만
    h = in_step * math.sqrt(3) / 2
    y, row = 40.0, 0
    while y < C:
        x = 150.0 + (in_step / 2 if row % 2 else 0)
        while x < 362:
            px, py = x + rnd.uniform(-3, 3), y + rnd.uniform(-3, 3)
            if inside(px, py, poly) and dist_edge(px, py, poly) > in_step * 0.55:
                out.append((px, py, in_size * (1 + rnd.uniform(-0.25, 0.25)), rnd.uniform(0, 60)))
            x += in_step
        y += h
        row += 1
    return out, poly


def svg(name, bg, color, edge_step, edge_size, in_step, in_size, width, seed, sil_opacity, branches=True):
    flakes, poly = leaf_flakes(edge_step, edge_size, in_step, in_size, seed, branches)
    sil = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in poly) + "Z"
    d = []
    sils = []
    for deg in (45, 135, 225, 315):
        sils.append(f'<path d="{sil}" transform="rotate({deg} 256 256)"/>')
        for x, y, r, a in flakes:
            fx, fy = rot(x, y, deg)
            d.append(flake(fx, fy, r, a + deg, branches))
    # 줄기: 작은 결정이 이어진 선 (두 아래 잎 사이로)
    rnd = random.Random(seed + 9)
    stem = []
    for i in range(5):  # 잎 아래(y≥400)에서 시작해 오른쪽으로 휘어진다 — 잎 위에 겹치지 않게
        t = i / 4
        stem.append(flake(258 + 10 * t + 40 * t * t, 404 + 50 * t, 7.5 + rnd.uniform(-1, 1), rnd.uniform(0, 60), False))
    OUT.joinpath(name).write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">\n'
        '  <!-- 눈 결정으로 이루어진 네잎클로버 (crystal_logo.py 로 생성) -->\n'
        f'  {bg}\n'
        f'  <g fill="{color}" opacity="{sil_opacity}">{"".join(sils)}</g>\n'
        f'  <path d="{"".join(stem)}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" fill="none"/>\n'
        f'  <path d="{"".join(d)}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" fill="none"/>\n'
        '</svg>\n', encoding="utf-8")


TEAL = "#2F6F62"
svg("E_결정잎_청록바탕.svg", f'<rect width="512" height="512" rx="112" fill="{TEAL}"/>', "#FFFFFF", 17, 9, 30, 8, 2.4, 3, 0.14)
svg("F_결정잎_흰바탕.svg", '<rect width="512" height="512" rx="112" fill="#FFFFFF"/>', TEAL, 17, 9, 30, 8, 2.4, 3, 0.10)
svg("G_큰결정잎_민트바탕.svg", '<rect width="512" height="512" rx="112" fill="#EAF4F1"/>', TEAL, 26, 13, 44, 12, 3.2, 11, 0.0)
svg("H_촘촘한결정_청록원.svg", f'<rect width="512" height="512" fill="#FFFFFF"/><circle cx="256" cy="256" r="240" fill="{TEAL}"/>',
    "#F2FAFB", 12, 6, 18, 6, 1.8, 5, 0.18, branches=False)
print("ok")
