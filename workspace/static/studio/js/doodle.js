/* 창작콘텐츠 › 그리기 엔진 (2026-10-22).
 *
 * 장면 하나를 "그림(SVG) + 글자 목록" 으로 만든다. 화면에서는 둘을 한 SVG 로 붙여 보여 주고,
 * PNG·MP4 로 저장할 때는 그림 SVG 를 캔버스에 그린 뒤 글자를 캔버스 글꼴로 따로 쓴다
 * (SVG 이미지 안에서는 웹 글꼴을 못 쓰기 때문).
 *
 * 마감(finish) 셋: paint(그림판) · pencil(연필 손그림) · clean(깔끔 일러스트).
 * 같은 장면 코드가 마감마다 선 떨림·두께·색·글꼴만 달리해 그린다.
 * 선 떨림은 도형 좌표에서 씨앗을 만들어 같은 그림은 늘 같은 모양이 된다. boil 값을 바꾸면 선이 살짝 다시 그려진다
 * (손그림 애니메이션의 '선 떨림'). 움직임은 group() 변환으로 줘야 떨림이 안 바뀐다.
 */
(function (global) {
  "use strict";

  const FONT = { hand: "CC Gaegu", title: "CC Jua" };

  const FINISHES = {
    paint: {
      label: "그림판", ink: "#141414", w: 7, jitter: 3.4, step: 16, crisp: true, misreg: 0, double: false, overshoot: 0,
      font: FONT.hand, weight: 700, grain: false, shadow: false,
      pal: { bg: "#ffffff", paper: "#ffffff", white: "#ffffff", fridge: "#ffffff", inside: "#fff7b0", light: "#fff200",
        ice: "#99d9ea", iceDeep: "#e3f6fb", red: "#ed1c24", gray: "#c3c3c3", dark: "#3f3f3f", pink: "#ffaec9",
        green: "#b5e61d", blue: "#00a2e8", orange: "#ffc90e", floor: "#141414", soft: "#7f7f7f", screen: "#22b14c" },
    },
    pencil: {
      label: "연필 손그림", ink: "#2b2a28", w: 4.2, jitter: 2.3, step: 20, crisp: false, misreg: 7, double: true, overshoot: 9,
      font: FONT.hand, weight: 700, grain: true, shadow: false,
      pal: { bg: "#fbf7ee", paper: "#fbf7ee", white: "#fffdf8", fridge: "#fffdf8", inside: "#f8ecb4", light: "#f4d35e",
        ice: "#bfdfee", iceDeep: "#e6f2f6", red: "#d9634f", gray: "#d6d2c8", dark: "#5a5650", pink: "#f0bdb5",
        green: "#b8cf8a", blue: "#6aa7c9", orange: "#eebd6a", floor: "#2b2a28", soft: "#8d877c", screen: "#7fae6b" },
    },
    clean: {
      label: "깔끔 일러스트", ink: "#2d2a32", w: 5.5, jitter: 0, step: 40, crisp: false, misreg: 0, double: false, overshoot: 0,
      font: FONT.title, weight: 400, grain: false, shadow: true,
      pal: { bg: "#fff6ec", paper: "#fff6ec", white: "#ffffff", fridge: "#eef3f8", inside: "#fff1bf", light: "#ffd84d",
        ice: "#a9dcf3", iceDeep: "#e4f4fb", red: "#ff6b5b", gray: "#d9d4e0", dark: "#4a4453", pink: "#ffc7bd",
        green: "#9fd8a8", blue: "#5aa9e6", orange: "#ffb84d", floor: "#2d2a32", soft: "#8e8698", screen: "#7dd3a0" },
    },
  };

  // ---------- 작은 도구 ----------
  function rng(seed) {
    let s = (seed >>> 0) || 0x9e3779b9;
    return () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
  }
  function hash(nums, salt) {
    let h = 2166136261 ^ salt;
    for (const n of nums) { h ^= Math.round(n * 10); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const easeOut = (t) => 1 - Math.pow(1 - t, 3);
  const easeBack = (t) => { const c = 1.7; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const f1 = (n) => Math.round(n * 10) / 10;

  function mul(m, n) {
    return [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1], m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
      m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]];
  }

  let measureCtx = null;
  function measure(text, size, family, weight) {
    if (!measureCtx) measureCtx = document.createElement("canvas").getContext("2d");
    measureCtx.font = `${weight || 400} ${size}px "${family}"`;
    return measureCtx.measureText(text).width;
  }

  // 점 목록을 일정 간격으로 다시 나눈다 (긴 선도 군데군데 떨리게)
  function resample(pts, step, closed) {
    const src = closed ? [...pts, pts[0]] : pts;
    const out = [src[0]];
    for (let i = 1; i < src.length; i++) {
      const [x0, y0] = src[i - 1], [x1, y1] = src[i];
      const d = Math.hypot(x1 - x0, y1 - y0), n = Math.max(1, Math.round(d / step));
      for (let k = 1; k <= n; k++) out.push([lerp(x0, x1, k / n), lerp(y0, y1, k / n)]);
    }
    if (closed) out.pop();
    return out;
  }

  // 낮은 주파수 흔들림 (마우스로 그은 선처럼 크게 휘고 작게 떨린다)
  function wobble(pts, amp, r, closed) {
    if (!amp) return pts;
    const n = pts.length, knots = Math.max(2, Math.ceil(n / 4) + 1), kv = [], kv2 = [];
    for (let i = 0; i < knots; i++) { kv.push(r() * 2 - 1); kv2.push(r() * 2 - 1); }
    if (closed) { kv[knots - 1] = kv[0]; kv2[knots - 1] = kv2[0]; }
    return pts.map(([x, y], i) => {
      const u = (i / Math.max(1, n - (closed ? 0 : 1))) * (knots - 1), k = Math.min(knots - 2, Math.floor(u)), t = u - k;
      const s = (1 - Math.cos(t * Math.PI)) / 2;
      const dx = lerp(kv[k], kv[k + 1], s) * amp + (r() - .5) * amp * .35;
      const dy = lerp(kv2[k], kv2[k + 1], s) * amp + (r() - .5) * amp * .35;
      return [x + dx, y + dy];
    });
  }

  // Catmull-Rom → 베지어 (부드러운 선)
  function smoothPath(p, closed) {
    if (p.length < 2) return "";
    if (p.length === 2) return `M${f1(p[0][0])} ${f1(p[0][1])}L${f1(p[1][0])} ${f1(p[1][1])}`;
    const n = p.length, g = (i) => closed ? p[(i + n) % n] : p[clamp(i, 0, n - 1)];
    let d = `M${f1(p[0][0])} ${f1(p[0][1])}`;
    const last = closed ? n : n - 1;
    for (let i = 0; i < last; i++) {
      const p0 = g(i - 1), p1 = g(i), p2 = g(i + 1), p3 = g(i + 2);
      const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
      const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
      d += `C${f1(c1[0])} ${f1(c1[1])} ${f1(c2[0])} ${f1(c2[1])} ${f1(p2[0])} ${f1(p2[1])}`;
    }
    return d + (closed ? "Z" : "");
  }

  // ---------- 도형 점 만들기 ----------
  function ellipsePts(cx, cy, rx, ry, a0 = 0, a1 = Math.PI * 2) {
    const full = Math.abs(a1 - a0) >= Math.PI * 2 - 1e-6;
    const n = Math.max(14, Math.round((rx + ry) * Math.abs(a1 - a0) / 24));
    const out = [];
    for (let i = 0; i < (full ? n : n + 1); i++) {
      const a = a0 + (a1 - a0) * i / n;
      out.push([cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]);
    }
    return out;
  }
  function rectPts(x, y, w, h, r = 0) {
    r = Math.min(r, w / 2, h / 2);
    if (!r) return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];
    const out = [], arc = (cx, cy, a0) => { for (let i = 0; i <= 4; i++) { const a = a0 + i * Math.PI / 8; out.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]); } };
    arc(x + w - r, y + r, -Math.PI / 2); arc(x + w - r, y + h - r, 0); arc(x + r, y + h - r, Math.PI / 2); arc(x + r, y + r, Math.PI);
    return out;
  }

  // ---------- 장면 ----------
  class Scene {
    constructor(w, h, finish, opts = {}) {
      this.w = w; this.h = h; this.key = finish; this.f = FINISHES[finish] || FINISHES.paint; this.c = this.f.pal;
      this.boil = opts.boil || 0; this.t = opts.t === undefined ? Infinity : opts.t;
      this.parts = []; this.texts = []; this.stack = [{ m: [1, 0, 0, 1, 0, 0], a: 1 }];
      this.uid = "s" + Math.random().toString(36).slice(2, 8);
    }
    get top() { return this.stack[this.stack.length - 1]; }

    // 애니메이션: 시작 시각부터 dur 동안 0→1 (멈춤 화면이면 늘 1)
    p(start, dur = .35) { return this.t === Infinity ? 1 : clamp((this.t - start) / dur, 0, 1); }
    on(start) { return this.t >= start; }
    pop(start, dur = .32) { const k = this.p(start, dur); return { s: k >= 1 ? 1 : lerp(.6, 1, easeBack(k)), a: clamp(k * 2.5, 0, 1) }; }
    fade(start, dur = .3) { return easeOut(this.p(start, dur)); }

    group(o, fn) {
      const x = o.x || 0, y = o.y || 0, s = o.s === undefined ? 1 : o.s, sy = o.sy === undefined ? s : o.sy, r = (o.r || 0) * Math.PI / 180;
      const ox = o.ox || 0, oy = o.oy || 0, a = o.a === undefined ? 1 : o.a;
      if (a <= 0.001) return;
      const cos = Math.cos(r), sin = Math.sin(r);
      let m = [1, 0, 0, 1, x + ox, y + oy];
      m = mul(m, [cos, sin, -sin, cos, 0, 0]);
      m = mul(m, [s, 0, 0, sy, 0, 0]);
      m = mul(m, [1, 0, 0, 1, -ox, -oy]);
      const full = mul(this.top.m, m);
      this.parts.push(`<g transform="matrix(${m.map((v) => +v.toFixed(4)).join(" ")})"${a < 1 ? ` opacity="${a.toFixed(3)}"` : ""}>`);
      this.stack.push({ m: full, a: this.top.a * a });
      fn();
      this.stack.pop();
      this.parts.push("</g>");
    }

    // 점 목록 하나를 마감에 맞게 그린다. o: fill, stroke(false|색), w, closed, rough(떨림 배수)
    shape(pts, o = {}) {
      const f = this.f, closed = !!o.closed, rough = o.rough === undefined ? 1 : o.rough;
      const seed = hash(pts.slice(0, 3).flat(), this.boil * 7919 + (o.salt || 0));
      const r = rng(seed);
      const base = resample(pts, f.step, closed);
      const amp = f.jitter * rough * (o.amp || 1);
      const stroke = o.stroke === false ? null : (o.stroke || f.ink);
      const w = (o.w || f.w) * (o.ws || 1);
      const crisp = f.crisp ? ' shape-rendering="crispEdges"' : "";
      const out = [];
      if (o.fill && o.fill !== "none") {
        let fp = closed ? base : base;
        if (f.misreg && rough) {
          const dx = (r() - .5) * f.misreg * 2, dy = (r() - .5) * f.misreg * 2;
          fp = wobble(base.map(([x, y]) => [x + dx, y + dy]), amp * 1.4, r, closed);
        } else fp = wobble(base, amp, rng(seed), closed);
        if (f.shadow && o.shadow !== false && closed) {
          out.push(`<path d="${smoothPath(fp.map(([x, y]) => [x + 7, y + 8]), true)}" fill="${f.ink}" opacity=".12"/>`);
        }
        out.push(`<path d="${smoothPath(fp, closed)}" fill="${o.fill}"${o.fillOpacity ? ` fill-opacity="${o.fillOpacity}"` : ""}${crisp}/>`);
      }
      if (stroke) {
        let sp = wobble(base, amp, rng(seed), closed), sc = closed;
        if (f.overshoot && closed && rough) { // 연필: 끝이 시작점을 살짝 지나쳐 겹친다
          sp = [...sp, ...sp.slice(0, 2).map(([x, y]) => [x + (r() - .5) * f.overshoot, y + (r() - .5) * f.overshoot])];
          sc = false;
        }
        const dash = o.dash ? ` stroke-dasharray="${o.dash}"` : "";
        out.push(`<path d="${smoothPath(sp, sc)}" fill="none" stroke="${stroke}" stroke-width="${f1(w)}" stroke-linecap="round" stroke-linejoin="round"${dash}${crisp}/>`);
        if (f.double && rough && !o.dash) {
          const sp2 = wobble(base, amp * 1.3, rng(seed ^ 0x5bd1e995), closed);
          out.push(`<path d="${smoothPath(sp2, closed)}" fill="none" stroke="${stroke}" stroke-width="${f1(w * .55)}" stroke-linecap="round" opacity=".45"/>`);
        }
      }
      this.parts.push(out.join(""));
    }

    line(pts, o = {}) { this.shape(pts, { ...o, closed: false }); }
    ellipse(cx, cy, rx, ry, o = {}) { this.shape(ellipsePts(cx, cy, rx, ry), { ...o, closed: true }); }
    arc(cx, cy, rx, ry, a0, a1, o = {}) { this.shape(ellipsePts(cx, cy, rx, ry, a0, a1), { ...o, closed: false }); }
    rect(x, y, w, h, r, o = {}) { this.shape(rectPts(x, y, w, h, r), { ...o, closed: true }); }
    poly(pts, o = {}) { this.shape(pts, { ...o, closed: true }); }
    dot(x, y, r, color) { this.shape(ellipsePts(x, y, r, r), { closed: true, fill: color || this.f.ink, stroke: false, rough: .3 }); }
    raw(svg) { this.parts.push(svg); }

    // 글자. lines 는 \n 으로 나눈다. o: size, anchor(start|middle|end), color, font(hand|title), weight, lh, r(도)
    text(str, x, y, o = {}) {
      const size = o.size || 48, family = o.font === "title" ? FONT.title : (o.font === "hand" ? FONT.hand : this.f.font);
      const weight = o.weight || (family === FONT.hand ? 700 : 400);
      const lines = String(str).split("\n"), lh = o.lh || 1.28;
      const alpha = this.top.a * (o.a === undefined ? 1 : o.a);
      if (alpha <= 0.001) return;
      this.texts.push({ lines, x, y, size, family, weight, lh, anchor: o.anchor || "middle", color: o.color || this.f.ink,
        r: o.r || 0, m: this.top.m.slice(), a: alpha, stroke: o.outline || null, vcenter: !!o.vcenter });
    }
    measure(str, size, font) {
      const family = font === "title" ? FONT.title : (font === "hand" ? FONT.hand : this.f.font);
      return Math.max(...String(str).split("\n").map((l) => measure(l, size, family, family === FONT.hand ? 700 : 400)));
    }

    // ---------- SVG 로 ----------
    background() {
      const c = this.c;
      let s = `<rect width="${this.w}" height="${this.h}" fill="${c.bg}"/>`;
      if (this.f.grain) {
        s += `<filter id="${this.uid}g" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="3"/>` +
          `<feColorMatrix values="0 0 0 0 .35  0 0 0 0 .3  0 0 0 0 .22  0 0 0 .09 0"/></filter>` +
          `<rect width="${this.w}" height="${this.h}" filter="url(#${this.uid}g)"/>`;
      }
      return s;
    }
    artSVG() {
      return `<svg xmlns="http://www.w3.org/2000/svg" width="${this.w}" height="${this.h}" viewBox="0 0 ${this.w} ${this.h}">${this.background()}${this.parts.join("")}</svg>`;
    }
    textSVG() {
      return this.texts.map((t) => {
        const anchor = { start: "start", middle: "middle", end: "end" }[t.anchor];
        const off = t.vcenter ? -((t.lines.length - 1) * t.size * t.lh) / 2 + t.size * .34 : 0;
        const spans = t.lines.map((l, i) => `<tspan x="0" y="${f1(off + i * t.size * t.lh)}">${esc(l)}</tspan>`).join("");
        const stroke = t.stroke ? ` stroke="${t.stroke}" stroke-width="${f1(t.size * .16)}" paint-order="stroke" stroke-linejoin="round"` : "";
        return `<g transform="matrix(${t.m.map((v) => +v.toFixed(4)).join(" ")})"><text transform="translate(${f1(t.x)} ${f1(t.y)}) rotate(${t.r})" ` +
          `font-family="'${t.family}'" font-weight="${t.weight}" font-size="${t.size}" text-anchor="${anchor}" fill="${t.color}"${t.a < 1 ? ` opacity="${t.a.toFixed(3)}"` : ""}${stroke}>${spans}</text></g>`;
      }).join("");
    }
    toSVG(cls) {
      return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${this.w} ${this.h}"${cls ? ` class="${cls}"` : ""} role="img">${this.background()}${this.parts.join("")}${this.textSVG()}</svg>`;
    }

    // ---------- 캔버스로 (저장용) ----------
    async drawTo(ctx2d) {
      const blob = new Blob([this.artSVG()], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);
      try {
        const img = new Image();
        img.src = url;
        await img.decode();
        ctx2d.setTransform(1, 0, 0, 1, 0, 0);
        ctx2d.globalAlpha = 1;
        ctx2d.drawImage(img, 0, 0, this.w, this.h);
      } finally { URL.revokeObjectURL(url); }
      for (const t of this.texts) {
        const m = t.m;
        ctx2d.setTransform(m[0], m[1], m[2], m[3], m[4], m[5]);
        ctx2d.translate(t.x, t.y);
        ctx2d.rotate(t.r * Math.PI / 180);
        ctx2d.globalAlpha = t.a;
        ctx2d.font = `${t.weight} ${t.size}px "${t.family}"`;
        ctx2d.textAlign = t.anchor === "middle" ? "center" : t.anchor === "end" ? "right" : "left";
        ctx2d.textBaseline = "alphabetic";
        const off = t.vcenter ? -((t.lines.length - 1) * t.size * t.lh) / 2 + t.size * .34 : 0;
        t.lines.forEach((l, i) => {
          const y = off + i * t.size * t.lh;
          if (t.stroke) { ctx2d.lineWidth = t.size * .16; ctx2d.lineJoin = "round"; ctx2d.strokeStyle = t.stroke; ctx2d.strokeText(l, 0, y); }
          ctx2d.fillStyle = t.color; ctx2d.fillText(l, 0, y);
        });
      }
      ctx2d.setTransform(1, 0, 0, 1, 0, 0);
      ctx2d.globalAlpha = 1;
    }
  }

  // ---------- 공용 소품 ----------
  // 나: 발 가운데가 (0,0). 키는 약 350. face: blank|puzzled|shock|happy|sad|tired, pose: down|reach|up|hold|point
  function me(S, x, y, o = {}) {
    const c = S.c, face = o.face || "blank", pose = o.pose || "down";
    S.group({ x, y, s: o.s || 1, sy: (o.s || 1) * (o.squash || 1) }, () => {
      S.group({ s: o.flip ? -1 : 1, sy: 1 }, () => {
        // 다리
        S.line([[-22, -66], [-26, -4], [-44, -2]]);
        S.line([[22, -66], [27, -4], [45, -3]]);
        // 팔
        const arms = {
          down: [[[-44, -150], [-62, -116], [-70, -88]], [[44, -150], [62, -116], [70, -88]]],
          reach: [[[-44, -150], [-62, -116], [-70, -88]], [[44, -150], [96, -160], [140, -168]]],
          up: [[[-44, -150], [-80, -190], [-96, -232]], [[44, -150], [80, -190], [96, -232]]],
          hold: [[[-44, -150], [-30, -112], [6, -104]], [[44, -150], [30, -112], [-6, -104]]],
          point: [[[-44, -150], [-62, -116], [-70, -88]], [[44, -150], [88, -186], [118, -222]]],
          door: [[[-44, -150], [-62, -116], [-70, -88]], [[44, -150], [100, -150], [150, -140]]],
        }[pose];
        arms.forEach((a) => S.line(a));
        // 몸통
        S.rect(-48, -172, 96, 110, 30, { fill: c.white });
        // 머리
        S.ellipse(0, -246, 80, 72, { fill: c.white });
        // 머리카락 한 가닥
        S.line([[-6, -316], [-2, -340], [12, -350], [24, -340], [16, -328], [6, -334]], { ws: .8 });
        // 얼굴
        const ink = S.f.ink;
        if (face === "shock") {
          S.ellipse(-28, -256, 15, 17, { fill: c.white, ws: .7 }); S.ellipse(28, -256, 15, 17, { fill: c.white, ws: .7 });
          S.dot(-27, -253, 5); S.dot(29, -253, 5);
          S.ellipse(0, -206, 13, 18, { fill: c.dark, ws: .7 });
        } else if (face === "happy") {
          S.arc(-28, -248, 13, 11, Math.PI * 1.1, Math.PI * 1.9, { ws: .8 }); S.arc(28, -248, 13, 11, Math.PI * 1.1, Math.PI * 1.9, { ws: .8 });
          S.arc(0, -224, 22, 16, Math.PI * .1, Math.PI * .9, { ws: .8 });
        } else if (face === "sad") {
          S.dot(-27, -246, 6); S.dot(27, -246, 6);
          S.line([[-44, -264], [-18, -276]], { ws: .7 }); S.line([[44, -264], [18, -276]], { ws: .7 });
          S.arc(0, -200, 18, 11, Math.PI * 1.15, Math.PI * 1.85, { ws: .8 });
        } else if (face === "tired") {
          S.line([[-40, -252], [-14, -252]], { ws: .8 }); S.line([[14, -252], [40, -252]], { ws: .8 });
          S.dot(-27, -245, 4.5); S.dot(27, -245, 4.5);
          S.line([[-10, -210], [12, -212]], { ws: .7 });
        } else if (face === "puzzled") {
          S.dot(-27, -250, 6); S.dot(27, -250, 6);
          S.line([[14, -282], [42, -290]], { ws: .7 });
          S.ellipse(10, -212, 7, 6, { fill: ink, stroke: false, rough: .3 });
        } else { // blank
          S.dot(-27, -250, 6); S.dot(27, -250, 6);
          S.line([[-14, -212], [14, -212]], { ws: .75 });
        }
      });
    });
  }

  // 냉장고: 왼쪽 위가 (0,0), 340×720. open: 아래 문 열림, freezer: 위 문 열림, light: 안쪽 불
  function fridge(S, x, y, o = {}) {
    const c = S.c;
    S.group({ x, y, s: o.s || 1 }, () => {
      S.rect(0, 0, 340, 720, 26, { fill: c.fridge });
      // 위 칸 (냉동실)
      if (o.freezer) {
        S.rect(16, 16, 308, 208, 12, { fill: c.iceDeep, ws: .7 });
        S.line([[30, 120], [310, 120]], { ws: .5 });
        S.poly([[340, 8], [462, -24], [462, 262], [340, 232]], { fill: c.fridge });
        S.line([[440, 30], [440, 210]], { ws: .7 });
      } else {
        S.line([[300, 110], [300, 196]], { ws: 1.2 });
      }
      S.line([[0, 240], [340, 240]]);
      // 아래 칸 (냉장실)
      if (o.open) {
        S.rect(16, 256, 308, 448, 12, { fill: o.light === false ? c.gray : c.inside, ws: .7 });
        S.line([[24, 410], [316, 410]], { ws: .6 }); S.line([[24, 560], [316, 560]], { ws: .6 });
        if (o.light !== false) S.ellipse(278, 286, 18, 14, { fill: c.light, ws: .6 });
        S.poly([[340, 248], [470, 206], [470, 774], [340, 716]], { fill: c.fridge });
        S.line([[360, 360], [452, 334]], { ws: .55 }); S.line([[360, 520], [452, 506]], { ws: .55 });
        S.line([[450, 290], [450, 420]], { ws: 1.1 });
      } else {
        S.line([[300, 290], [300, 430]], { ws: 1.2 });
      }
      // 다리
      S.line([[34, 720], [34, 740]]); S.line([[306, 720], [306, 740]]);
    });
  }

  // 빛줄기: (x,y) 에서 a0~a1 방향으로
  function rays(S, x, y, n, r0, r1, a0, a1, color, o = {}) {
    for (let i = 0; i < n; i++) {
      const a = (a0 + (a1 - a0) * (n === 1 ? .5 : i / (n - 1))) * Math.PI / 180;
      S.line([[x + Math.cos(a) * r0, y + Math.sin(a) * r0], [x + Math.cos(a) * r1, y + Math.sin(a) * r1]], { stroke: color || S.c.light, ws: o.ws || 1.1, salt: i });
    }
  }

  // 전구: 가운데 (0,0), 반지름 50
  function bulb(S, x, y, o = {}) {
    const c = S.c;
    S.group({ x, y, s: o.s || 1 }, () => {
      if (o.on) rays(S, 0, -8, 9, 74, 112, -200, 20, c.orange);
      S.shape([...ellipsePts(0, -10, 50, 50, Math.PI * .75, Math.PI * 2.25), [20, 46], [-20, 46]], { closed: true, fill: o.on ? c.light : c.gray });
      S.rect(-22, 46, 44, 30, 6, { fill: c.white, ws: .8 });
      S.line([[-22, 56], [22, 56]], { ws: .6 }); S.line([[-22, 66], [22, 66]], { ws: .6 });
      if (o.on) { S.line([[-9, 46], [-9, 14]], { ws: .6 }); S.line([[9, 46], [9, 14]], { ws: .6 }); S.arc(0, 10, 9, 9, Math.PI, Math.PI * 2, { ws: .6 }); }
      else { S.line([[-12, -24], [12, 0]], { ws: .7, stroke: c.soft }); S.line([[12, -24], [-12, 0]], { ws: .7, stroke: c.soft }); }
    });
  }

  // 얼음 덩어리: 가운데 (0,0)
  function ice(S, x, y, label, o = {}) {
    const c = S.c, w = o.w || 230, h = o.h || 120;
    S.group({ x, y, r: o.r || 0, s: o.s || 1 }, () => {
      S.rect(-w / 2, -h / 2, w, h, 18, { fill: c.ice });
      S.line([[-w / 2 + 16, -h / 2 + 30], [-w / 2 + 16, -h / 2 + 14], [-w / 2 + 40, -h / 2 + 12]], { stroke: c.white, ws: 1.1 });
      if (label) S.text(label, 0, 0, { size: o.size || 38, vcenter: true });
    });
  }

  // 전자레인지: 왼쪽 위 (0,0), 440×270
  function microwave(S, x, y, o = {}) {
    const c = S.c;
    S.group({ x, y, s: o.s || 1 }, () => {
      S.rect(0, 0, 440, 270, 22, { fill: c.white });
      if (o.doorOpen) {
        S.rect(24, 30, 280, 210, 10, { fill: c.inside, ws: .8 });
        S.poly([[24, 24], [-90, -20], [-90, 290], [24, 246]], { fill: c.white });
        S.rect(-70, 30, 70, 210, 8, { fill: c.gray, ws: .6, rough: .6 });
      } else {
        S.rect(24, 30, 280, 210, 10, { fill: o.on ? c.inside : c.dark, ws: .8 });
      }
      S.line([[318, 20], [318, 250]], { ws: .7 });
      S.rect(332, 34, 86, 44, 6, { fill: c.dark, ws: .7 });
      if (o.time) S.text(o.time, 375, 66, { size: 32, color: c.screen, font: "title" });
      for (let i = 0; i < 2; i++) for (let j = 0; j < 2; j++) S.rect(338 + j * 42, 94 + i * 30, 32, 20, 5, { fill: c.gray, ws: .5, rough: .5, salt: i * 2 + j });
      S.rect(334, 166, 84, 60, 10, { fill: o.pressed ? c.orange : c.red, ws: .8 });
      if (o.btn) S.text(o.btn, 376, 206, { size: 30, color: c.white, font: "title" });
      S.line([[40, 270], [40, 284]]); S.line([[400, 270], [400, 284]]);
    });
  }

  // 말풍선: 가운데 (x,y) 에 글자, tail 은 꼬리 끝 [x,y]. kind: say|think|shout
  function bubble(S, x, y, str, o = {}) {
    const c = S.c, size = o.size || 46, kind = o.kind || "say";
    const tw = S.measure(str, size), lines = String(str).split("\n").length;
    const w = Math.max(tw + size * 1.4, size * 3), h = lines * size * 1.28 + size * 1.0;
    S.group({ x, y, s: o.s || 1, a: o.a }, () => {
      const tail = o.tail ? [o.tail[0] - x, o.tail[1] - y] : null;
      if (kind === "think") {
        S.shape(cloudPts(w / 2 + 10, h / 2 + 6), { closed: true, fill: o.fill || c.white });
        if (tail) {
          const ang = Math.atan2(tail[1], tail[0]), ex = Math.cos(ang) * (w / 2 + 14), ey = Math.sin(ang) * (h / 2 + 10);
          [.3, .6, .88].forEach((k, i) => S.ellipse(lerp(ex, tail[0], k), lerp(ey, tail[1], k), 17 - i * 4.5, 14 - i * 3.6, { fill: o.fill || c.white, ws: .7, salt: i }));
        }
      } else if (kind === "shout") {
        const pts = [], n = 18;
        for (let i = 0; i < n; i++) {
          const a = i / n * Math.PI * 2, k = i % 2 ? 1 : 1.16;
          pts.push([Math.cos(a) * (w / 2 + 16) * k, Math.sin(a) * (h / 2 + 18) * k]);
        }
        S.poly(pts, { fill: o.fill || c.white });
        if (tail) S.poly([[tail[0] * .55 - 16, tail[1] * .55], [tail[0], tail[1]], [tail[0] * .55 + 10, tail[1] * .55 + 22]], { fill: o.fill || c.white, ws: .9 });
        if (tail) S.line([[tail[0] * .5 - 12, tail[1] * .5 - 4], [tail[0] * .5 + 12, tail[1] * .5 + 22]], { stroke: o.fill || c.white, ws: 2.6, rough: 0 });
      } else {
        if (tail) {
          const ang = Math.atan2(tail[1], tail[0]), bx = Math.cos(ang) * w * .32, by = Math.sin(ang) * h * .32;
          const px = -Math.sin(ang) * 26, py = Math.cos(ang) * 26;
          S.poly([[bx + px, by + py], [tail[0], tail[1]], [bx - px, by - py]], { fill: o.fill || c.white, ws: .9 });
        }
        S.ellipse(0, 0, w / 2 + 6, h / 2 + 4, { fill: o.fill || c.white });
        if (tail) { // 꼬리와 몸 사이 선을 덮는다
          const ang = Math.atan2(tail[1], tail[0]), bx = Math.cos(ang) * w * .4, by = Math.sin(ang) * h * .4;
          S.ellipse(bx, by, 30, 26, { fill: o.fill || c.white, stroke: false, rough: 0, shadow: false });
        }
      }
      S.text(str, 0, 0, { size, vcenter: true, color: o.color });
    });
  }
  function cloudPts(rx, ry) {
    const out = [], bumps = 9;
    for (let i = 0; i < bumps; i++) {
      const a0 = i / bumps * Math.PI * 2, a1 = (i + 1) / bumps * Math.PI * 2;
      for (let k = 0; k <= 5; k++) {
        const a = lerp(a0, a1, k / 5), bump = Math.sin(k / 5 * Math.PI) * .13;
        out.push([Math.cos(a) * rx * (1 + bump), Math.sin(a) * ry * (1 + bump)]);
      }
    }
    return out;
  }

  // 화살표: 점 목록 끝에 촉
  function arrow(S, pts, o = {}) {
    S.line(pts, o);
    const [x1, y1] = pts[pts.length - 1], [x0, y0] = pts[pts.length - 2];
    const a = Math.atan2(y1 - y0, x1 - x0), L = o.head || 30;
    S.line([[x1 - Math.cos(a - .5) * L, y1 - Math.sin(a - .5) * L], [x1, y1], [x1 - Math.cos(a + .5) * L, y1 - Math.sin(a + .5) * L]], o);
  }

  function floor(S, x0, x1, y) { S.line([[x0, y], [x1, y]], { ws: .8, stroke: S.c.floor }); }

  async function ready() {
    if (!document.fonts) return;
    await Promise.all([
      document.fonts.load(`700 40px "${FONT.hand}"`, "가나다"),
      document.fonts.load(`400 40px "${FONT.hand}"`, "가나다"),
      document.fonts.load(`400 40px "${FONT.title}"`, "가나다"),
    ]);
  }

  global.Doodle = {
    FINISHES, Scene, ready, me, fridge, rays, bulb, ice, microwave, bubble, arrow, floor,
    util: { clamp, lerp, easeOut, easeBack, rng, ellipsePts, rectPts },
    works: {},
  };
})(window);
