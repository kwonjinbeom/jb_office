"""눈잎 로고 (3판): 잎 하나에 큰 눈 결정 몇 개 — 멀리서도 결정으로 보이게.

잎 = 하트(대각선 네 장, 가운데에서 조금 띄움). 잎마다 큰 결정 3개(두 볼록한 곳 + 아래 가운데).
결정은 팔 6개 + 팔마다 가지 한 쌍 + 끝 갈래. 잎 모양은 옅은 실루엣이나 가는 외곽선으로 보이게 한다.
"""
import math
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
C, K, GAP = 256.0, 5.0, 12.0
TEAL = "#2F6F62"


def heart_path():
    pts = []
    for i in range(200):
        t = 2 * math.pi * i / 200
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((C + K * x, C - GAP - K * (y + 17)))
    return "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"


def flake(x, y, r, angle):
    d = []
    for k in range(6):
        a = math.radians(angle + k * 60)
        ex, ey = x + r * math.cos(a), y + r * math.sin(a)
        d.append(f"M{x:.1f} {y:.1f}L{ex:.1f} {ey:.1f}")
        bx, by = x + r * 0.55 * math.cos(a), y + r * 0.55 * math.sin(a)
        for s in (-1, 1):  # 가운데 가지 한 쌍
            b = a + s * math.radians(50)
            d.append(f"M{bx:.1f} {by:.1f}L{bx + r * 0.36 * math.cos(b):.1f} {by + r * 0.36 * math.sin(b):.1f}")
        for s in (-1, 1):  # 끝 갈래
            b = a + s * math.radians(40)
            tx, ty = x + r * 0.82 * math.cos(a), y + r * 0.82 * math.sin(a)
            d.append(f"M{tx:.1f} {ty:.1f}L{tx + r * 0.2 * math.cos(b):.1f} {ty + r * 0.2 * math.sin(b):.1f}")
    return "".join(d)


# 위로 선 잎 하나 안의 결정 자리 (x, y, 반지름, 각도)
SPOTS = [(216, 150, 27, 0), (296, 150, 27, 30), (256, 198, 25, 15)]  # 두 볼록한 곳 + 아래 가운데


def rot(x, y, deg):
    a = math.radians(deg)
    dx, dy = x - C, y - C
    return C + dx * math.cos(a) - dy * math.sin(a), C + dx * math.sin(a) + dy * math.cos(a)


def svg(name, bg, color, width, sil_fill=0.0, outline=0.0):
    hp = heart_path()
    leaves, flakes = [], []
    for deg in (45, 135, 225, 315):
        leaves.append(f'<path d="{hp}" transform="rotate({deg} 256 256)"/>')
        for x, y, r, a in SPOTS:
            fx, fy = rot(x, y, deg)
            flakes.append(flake(fx, fy, r, a + deg))
    stem = "M258 402 C 262 424, 276 442, 302 458"  # 잎 아래에서 시작하는 가는 줄기
    layers = [bg]
    if sil_fill:
        layers.append(f'<g fill="{color}" opacity="{sil_fill}">{"".join(leaves)}</g>')
    if outline:
        layers.append(f'<g fill="none" stroke="{color}" stroke-width="{outline}" opacity="0.75">{"".join(leaves)}</g>')
    layers.append(f'<path d="{stem}" stroke="{color}" stroke-width="{width * 1.3:.1f}" stroke-linecap="round" fill="none"/>')
    layers.append(f'<path d="{"".join(flakes)}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" fill="none"/>')
    OUT.joinpath(name).write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">\n'
        '  <!-- 큰 눈 결정으로 이루어진 네잎클로버 (crystal_big.py 로 생성) -->\n  ' + "\n  ".join(layers) + "\n</svg>\n",
        encoding="utf-8")


svg("M_큰결정_청록바탕.svg", f'<rect width="512" height="512" rx="112" fill="{TEAL}"/>', "#FFFFFF", 3.4, sil_fill=0.16)
svg("N_큰결정_흰바탕.svg", '<rect width="512" height="512" fill="#FFFFFF"/>', TEAL, 3.4, sil_fill=0.12)
svg("O_큰결정_청록원_외곽선.svg", f'<rect width="512" height="512" fill="#FFFFFF"/><circle cx="256" cy="256" r="240" fill="{TEAL}"/>',
    "#FFFFFF", 3.4, outline=3)
svg("P_큰결정_민트바탕_외곽선.svg", '<rect width="512" height="512" rx="112" fill="#EAF4F1"/>', TEAL, 3.4, outline=3)
print("ok")
