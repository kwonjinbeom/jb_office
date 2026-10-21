/* 창작콘텐츠 › 생각꼬리 #1 「냉장고 앞에서 까먹는 이유」 컷 그림 (2026-10-22).
 * 컷마다 1080×1080 정사각 안에 그린다. 글자는 apps/studio/works.py 의 cuts[i].say 에서 받는다.
 * S.t 는 그 컷이 시작되고 지난 초 (카툰처럼 멈춘 화면이면 Infinity → 마지막 모습).
 */
(function (D) {
  "use strict";
  const { me, fridge, rays, bulb, ice, microwave, bubble, arrow, floor } = D;
  const { lerp, easeOut, clamp } = D.util;

  function popIn(S, start, x, y, fn, dur) {
    const p = S.pop(start, dur);
    if (p.a <= 0) return;
    S.group({ x, y, s: p.s, a: p.a }, fn);
  }
  function shake(S, start, dur, amp) {
    if (S.t === Infinity || S.t < start || S.t > start + dur) return [0, 0];
    const k = 1 - (S.t - start) / dur, f = Math.floor(S.t * 30);
    return [Math.sin(f * 2.3) * amp * k, Math.cos(f * 3.1) * amp * k];
  }

  const cuts = [
    // 1. 표지: 닫힌 냉장고 앞 물음표
    (S) => {
      floor(S, 60, 1020, 935);
      fridge(S, 560, 195);
      me(S, 330, 935, { s: 1.25, face: "puzzled" });
      popIn(S, .5, 405, 450, () => S.text("?", 0, 0, { size: 170, color: S.c.red, font: "title" }));
    },
    // 2. 문을 연다 → 뭐 하러 왔더라
    (S, say) => {
      const open = S.on(1.15);
      floor(S, 60, 1020, 935);
      if (open) S.group({ a: S.fade(1.15, .25) }, () => rays(S, 730, 660, 6, 250, 400, 150, 215, S.c.light, { ws: 1.4 }));
      fridge(S, 560, 195, { open });
      const walk = easeOut(S.p(0, 1.05));
      const bob = S.t !== Infinity && S.t < 1.05 ? Math.abs(Math.sin(S.t * 9)) * -10 : 0;
      me(S, lerp(120, 300, walk), 935 + bob, { s: 1.2, face: "blank" });
      const p = S.pop(2.3);
      if (p.a > 0) bubble(S, 330, 300, say.think, { kind: "think", tail: [320, 490], s: p.s, a: p.a, size: 52 });
    },
    // 3. 냉장고 불은 켜지고 나는 깜빡
    (S, say) => {
      S.line([[540, 70], [540, 1010]], { ws: .7 });
      const on = S.on(.5), off = S.on(1.9);
      bulb(S, 270, 440, { on, s: 1.9 });
      popIn(S, .5, 270, 820, () => S.text(say.left, 0, 0, { size: 92 }));
      me(S, 810, 1000, { s: .95, face: "blank" });
      bulb(S, 810, 520, { on: !off, s: 1.05 });
      popIn(S, 1.9, 810, 335, () => S.text(say.right, 0, 0, { size: 92, color: S.c.red }));
      popIn(S, 2.7, 810, 410, () => S.text("※ " + say.note, 0, 0, { size: 34, color: S.c.soft }));
    },
    // 4. 같은 콘센트
    (S, say) => {
      const c = S.c;
      floor(S, 40, 1040, 935);
      fridge(S, 50, 269, { s: .9 });
      // 멀티탭과 냉장고 선
      S.rect(360, 846, 430, 76, 20, { fill: c.white });
      S.line([[356, 760], [400, 740], [455, 748], [480, 796]], { ws: .8 });
      [480, 640].forEach((x, i) => { S.ellipse(x, 884, 26, 24, { fill: c.white, ws: .7, salt: i }); S.dot(x - 8, 884, 4); S.dot(x + 8, 884, 4); });
      S.rect(722, 866, 40, 38, 8, { fill: c.red, ws: .7 });
      popIn(S, .7, 480, 820, () => { S.rect(-24, -26, 48, 50, 8, { fill: c.dark }); });
      // 내 머리에서 나온 선
      const plug2 = S.pop(1.1);
      if (plug2.a > 0) {
        S.group({ a: plug2.a }, () => S.line([[748, 690], [700, 700], [660, 740], [640, 794]], { ws: .8 }));
        S.group({ x: 640, y: 820, s: plug2.s, a: plug2.a }, () => S.rect(-24, -26, 48, 50, 8, { fill: c.dark }));
      }
      const sad = S.on(2.5);
      me(S, 830, 935, { s: 1.15, face: sad ? "sad" : "blank" });
      S.text(say.a, 480, 990, { size: 40 });
      S.text(say.b, 640, 990, { size: 40 });
      const p = S.pop(2.5);
      if (p.a > 0) bubble(S, 760, 330, say.talk, { tail: [800, 520], s: p.s, a: p.a, size: 50 });
    },
    // 5. 생각이 얼어서 툭
    (S, say) => {
      floor(S, 40, 1040, 935);
      rays(S, 730, 660, 5, 260, 380, 160, 205, S.c.light, { ws: 1.2 });
      fridge(S, 560, 195, { open: true });
      me(S, 250, 935, { s: 1.2, face: "blank" });
      const morph = S.p(.5, .6), fall = easeOut(S.p(1.25, .75));
      const x = lerp(330, 720, fall), y = lerp(400, 562, fall) - Math.sin(fall * Math.PI) * 140;
      if (morph < 1) bubble(S, 330, 400, say.ice, { kind: "think", tail: [270, 530], a: 1 - morph, size: 44 });
      if (fall >= 1) [.2, .38, .56, .74].forEach((k, i) => {
        S.ellipse(lerp(330, 720, k), lerp(400, 562, k) - Math.sin(k * Math.PI) * 140, 13 - i * 2, 11 - i * 2, { fill: S.c.white, ws: .55, salt: i });
      });
      if (morph > 0) S.group({ a: morph }, () => ice(S, x, y, say.ice, { w: S.measure(say.ice, 38) + 60, h: 104, r: lerp(0, 9, fall) }));
      popIn(S, 2.0, 640, 470, () => S.text(say.drop, 0, 0, { size: 96, color: S.c.red, r: -8, outline: S.c.white }));
      if (S.on(2.0)) [[-60, -84], [0, -100], [60, -84]].forEach(([dx, dy], i) => S.line([[740 + dx * .7, 500 + dy * .3], [740 + dx, 500 + dy * .6]], { ws: .7, salt: i }));
    },
    // 6. 냉동실엔 까먹은 게 다
    (S, say) => {
      const c = S.c;
      S.rect(90, 80, 760, 880, 30, { fill: c.fridge });
      S.rect(125, 115, 690, 810, 16, { fill: c.iceDeep, ws: .7 });
      S.line([[135, 385], [805, 385]], { ws: .6 }); S.line([[135, 655], [805, 655]], { ws: .6 });
      const door = S.p(.2, .35);
      S.poly([[850, 90], [lerp(860, 965, door), lerp(86, 46, door)], [lerp(860, 965, door), lerp(954, 994, door)], [850, 950]], { fill: c.fridge });
      // 성에
      [[180, 150], [420, 140], [760, 160], [160, 900], [780, 890]].forEach(([x, y], i) => {
        S.line([[x - 14, y], [x + 14, y]], { ws: .5, stroke: c.blue, salt: i }); S.line([[x, y - 14], [x, y + 14]], { ws: .5, stroke: c.blue, salt: i + 9 });
      });
      const pos = [[300, 268], [640, 268], [300, 538], [640, 538], [300, 808], [640, 808]];
      say.items.forEach((label, i) => {
        const p = S.pop(.9 + i * .4);
        if (p.a <= 0) return;
        const last = i === say.items.length - 1;
        S.group({ x: pos[i][0], y: pos[i][1], s: p.s, a: p.a }, () => {
          ice(S, 0, 0, label, { w: 290, h: 128, size: 40, r: [-3, 2, 3, -2, -4, 3][i] });
          if (last) S.text("방금", 120, -72, { size: 34, color: c.red, r: 10 });
        });
      });
      me(S, 985, 1000, { s: .52, face: "puzzled" });
    },
    // 7. 해동하면 돌아올까
    (S, say) => {
      const c = S.c;
      S.rect(30, 853, 680, 200, 14, { fill: c.gray });
      const on = S.on(1.5);
      const left = on && S.t !== Infinity ? Math.max(0, 180 - (S.t - 1.5) * 47) : 180;
      const time = `${Math.floor(left / 60)}:${String(Math.floor(left % 60)).padStart(2, "0")}`;
      const pressed = S.t !== Infinity && S.on(.8) && !S.on(1.45);
      microwave(S, 90, 470, { s: 1.35, on, time, btn: say.btn, pressed });
      ice(S, 311, 652, "그 배우\n이름", { w: 200, h: 120, size: 32, r: on ? Math.sin((S.t === Infinity ? 0 : S.t) * 4) * 4 : 0 });
      me(S, 760, 985, { s: 1.05, face: "puzzled", pose: "point", flip: true });
      const p = S.pop(1.6);
      if (p.a > 0) bubble(S, 740, 270, say.talk, { tail: [770, 630], s: p.s, a: p.a, size: 50 });
    },
    // 8. 영어단어가 같이 녹았다
    (S, say) => {
      const c = S.c;
      S.rect(10, 900, 720, 160, 14, { fill: c.gray });
      microwave(S, 140, 560, { s: 1.2, doorOpen: true, time: "0:00" });
      popIn(S, .15, 470, 500, () => S.text("띵!", 0, 0, { size: 76, color: c.red, r: -6 }));
      // 김
      [0, 1, 2].forEach((i) => S.line([[280 + i * 60, 560], [265 + i * 60, 520], [290 + i * 60, 480], [272 + i * 60, 440]], { ws: .6, stroke: c.soft, salt: i }));
      const target = [[250, 150, -8, 66], [640, 120, 6, 60], [440, 290, 4, 70], [850, 240, -9, 54], [200, 420, 9, 56], [680, 400, -5, 62], [860, 620, 6, 50], [700, 520, -4, 50]];
      const from = [327, 722];
      say.words.forEach((w, i) => {
        const [tx, ty, r, size] = target[i];
        const k = easeOut(S.p(.8 + i * .13, .55));
        if (k <= 0) return;
        S.group({ x: lerp(from[0], tx, k), y: lerp(from[1], ty, k), s: lerp(.3, 1, k), r: r * k }, () => S.text(w, 0, 0, { size, outline: c.bg }));
      });
      me(S, 910, 990, { s: .95, face: "shock", pose: "up" });
    },
    // 9. 도는 화살표
    (S, say) => {
      const c = S.c, cx = 540, cy = 520, R = 260;
      const node = (i) => [cx + Math.cos((-90 + i * 90) * Math.PI / 180) * R, cy + Math.sin((-90 + i * 90) * Math.PI / 180) * R];
      // 아이콘
      const [hx, hy] = node(0);
      S.ellipse(hx, hy, 72, 64, { fill: c.white }); S.dot(hx - 24, hy - 4, 6); S.dot(hx + 24, hy - 4, 6);
      S.line([[hx - 4, hy - 62], [hx, hy - 86], [hx + 14, hy - 94], [hx + 24, hy - 84]], { ws: .7 });
      const [fx, fy] = node(1); fridge(S, fx - 48, fy - 104, { s: .28 });
      const [ix, iy] = node(2); ice(S, ix, iy, "", { w: 150, h: 92 });
      const [mx, my] = node(3); microwave(S, mx - 66, my - 41, { s: .3 });
      S.text(say.steps[0], hx + 100, hy + 14, { size: 42, anchor: "start" });
      S.text(say.steps[1], fx, fy + 145, { size: 42 });
      S.text(say.steps[2], ix, iy + 95, { size: 42 });
      S.text(say.steps[3], mx, my + 95, { size: 42 });
      for (let i = 0; i < 4; i++) {
        const a = S.fade(.6 + i * .7, .35);
        if (a <= 0) continue;
        const a0 = (-90 + i * 90 + 24) * Math.PI / 180, a1 = (-90 + i * 90 + 66) * Math.PI / 180;
        const pts = D.util.ellipsePts(cx, cy, R, R, a0, a0 + (a1 - a0) * a);
        if (pts.length > 1) S.group({}, () => arrow(S, pts, { stroke: c.red, ws: 1.1, head: 30, salt: i }));
      }
      me(S, cx, cy + 90, { s: .5, face: S.on(3.4) ? "happy" : "blank" });
      const p = S.pop(3.4);
      if (p.a > 0) bubble(S, 540, 975, say.talk, { kind: "think", s: p.s, a: p.a, size: 42 });
    },
    // 10. 엄마
    (S, say) => {
      const c = S.c;
      const [sx, sy] = shake(S, .25, .5, 14), [sx2, sy2] = shake(S, 3.3, .45, 10);
      S.group({ x: sx + sx2, y: sy + sy2 }, () => {
        floor(S, 40, 1040, 935);
        fridge(S, 140, 195, { open: true });
        me(S, 720, 935, { s: 1.15, face: "tired", pose: "door", flip: true });
      });
      let p = S.pop(.25);
      if (p.a > 0) bubble(S, 735, 150, say.mom, { kind: "shout", tail: [1080, 230], s: p.s, a: p.a, size: 50 });
      p = S.pop(3.3);
      if (p.a > 0) bubble(S, 805, 345, say.mom2, { tail: [1080, 400], s: p.s, a: p.a, size: 48 });
      p = S.pop(2.0);
      if (p.a > 0) bubble(S, 600, 495, say.me, { tail: [690, 585], s: p.s, a: p.a, size: 46 });
      popIn(S, 4.9, 540, 1040, () => S.text(say.end, 0, 0, { size: 44, color: c.soft }));
    },
  ];

  D.works.fridge = { cuts };
})(window.Doodle);
