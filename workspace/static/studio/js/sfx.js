/* 창작콘텐츠 › 효과음·배경음 (2026-10-22). 녹음 파일 없이 Web Audio 로 그때그때 합성한다.
 * 같은 함수가 재생(AudioContext)과 MP4 저장(OfflineAudioContext) 양쪽에 쓰인다.
 * 작품의 cuts[i].sfx = [[컷 안에서의 초, 이름], ...]. hum_on/hum_off 는 냉장고 웅웅 소리 구간, micro→ding 은 전자레인지 구간.
 */
(function (global) {
  "use strict";
  const noiseCache = new WeakMap();
  function noise(ctx) {
    let b = noiseCache.get(ctx);
    if (!b) {
      b = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
      const d = b.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
      noiseCache.set(ctx, b);
    }
    return b;
  }

  // 작은 부품: 음 하나 (주파수 미끄러짐 · 감쇠)
  function tone(ctx, out, t, o) {
    const osc = ctx.createOscillator(), g = ctx.createGain();
    osc.type = o.type || "sine";
    osc.frequency.setValueAtTime(o.f, t);
    if (o.f2) osc.frequency.exponentialRampToValueAtTime(o.f2, t + (o.slide || o.dur));
    const a = o.attack || .005, v = o.gain || .2;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(v, t + a);
    g.gain.exponentialRampToValueAtTime(0.0001, t + o.dur);
    let node = osc;
    if (o.lp) { const f = ctx.createBiquadFilter(); f.type = "lowpass"; f.frequency.value = o.lp; osc.connect(f); node = f; }
    node.connect(g); g.connect(out);
    osc.start(t); osc.stop(t + o.dur + .05);
  }
  // 잡음 한 번 (필터 · 감쇠 · 주파수 쓸기)
  function burst(ctx, out, t, o) {
    const src = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
    src.buffer = noise(ctx);
    f.type = o.filter || "bandpass";
    f.frequency.setValueAtTime(o.f || 1000, t);
    if (o.f2) f.frequency.exponentialRampToValueAtTime(o.f2, t + o.dur);
    f.Q.value = o.q || 1;
    const v = o.gain || .3, a = o.attack || .003;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(v, t + a);
    g.gain.exponentialRampToValueAtTime(0.0001, t + o.dur);
    src.connect(f); f.connect(g); g.connect(out);
    src.start(t, Math.random()); src.stop(t + o.dur + .05);
  }

  const FX = {
    pop: (c, o, t) => tone(c, o, t, { f: 520, f2: 980, dur: .09, gain: .18, slide: .06 }),
    steps: (c, o, t) => { for (let i = 0; i < 4; i++) { burst(c, o, t + i * .24, { filter: "lowpass", f: 420, dur: .07, gain: .45 }); tone(c, o, t + i * .24, { f: 95, f2: 60, dur: .08, gain: .25 }); } },
    door: (c, o, t) => {
      burst(c, o, t, { filter: "lowpass", f: 250, f2: 1400, dur: .22, gain: .5, attack: .02 });
      tone(c, o, t, { f: 80, f2: 55, dur: .16, gain: .35 });
      tone(c, o, t + .14, { f: 2350, dur: .14, gain: .05 }); tone(c, o, t + .21, { f: 3050, dur: .12, gain: .04 });
    },
    click: (c, o, t) => { burst(c, o, t, { filter: "highpass", f: 2200, dur: .012, gain: .7 }); burst(c, o, t + .075, { filter: "highpass", f: 1800, dur: .014, gain: .6 }); },
    blink: (c, o, t) => tone(c, o, t, { f: 920, f2: 210, dur: .32, gain: .16, slide: .28 }),
    plug: (c, o, t) => { burst(c, o, t, { filter: "highpass", f: 900, dur: .02, gain: .6 }); tone(c, o, t, { f: 190, f2: 120, dur: .06, gain: .2 }); },
    sad: (c, o, t) => [392, 370, 349, 311].forEach((f, i) => tone(c, o, t + i * .24, { type: "sawtooth", f, f2: i === 3 ? f * .94 : 0, dur: i === 3 ? .6 : .22, gain: .06, lp: 900, attack: .03 })),
    freeze: (c, o, t) => {
      [1760, 2350, 2790, 3520, 2093].forEach((f, i) => tone(c, o, t + i * .09, { f, dur: .5, gain: .035, attack: .03 }));
      for (let i = 0; i < 6; i++) burst(c, o, t + .2 + i * .07, { filter: "highpass", f: 5000, dur: .02, gain: .12 });
    },
    ice: (c, o, t) => { tone(c, o, t, { f: 160, f2: 55, dur: .14, gain: .6 }); burst(c, o, t, { filter: "lowpass", f: 700, dur: .05, gain: .4 }); tone(c, o, t + .01, { f: 2650, dur: .28, gain: .07 }); },
    beep: (c, o, t) => tone(c, o, t, { type: "square", f: 1990, dur: .085, gain: .045, attack: .002 }),
    ding: (c, o, t) => { tone(c, o, t, { f: 1760, dur: 1.4, gain: .2 }); tone(c, o, t, { f: 3520, dur: .9, gain: .06 }); tone(c, o, t, { f: 2637, dur: 1.1, gain: .05 }); },
    flood: (c, o, t) => {
      burst(c, o, t, { f: 300, f2: 3200, dur: 1.0, gain: .45, q: .8, attack: .25 });
      for (let i = 0; i < 9; i++) tone(c, o, t + .1 + i * .11, { f: 500 + (i % 4) * 160, f2: 900 + (i % 3) * 200, dur: .07, gain: .1 });
    },
    swish: (c, o, t) => burst(c, o, t, { f: 900, f2: 3400, dur: .2, gain: .3, q: 1.2, attack: .05 }),
    shout: (c, o, t) => {
      tone(c, o, t, { f: 110, f2: 50, dur: .25, gain: .5 });
      burst(c, o, t, { filter: "lowpass", f: 180, dur: .35, gain: .4 });
      tone(c, o, t + .02, { type: "square", f: 523, dur: .16, gain: .05 }); tone(c, o, t + .02, { type: "square", f: 659, dur: .16, gain: .04 });
    },
    shout2: (c, o, t) => { tone(c, o, t, { f: 100, f2: 50, dur: .2, gain: .35 }); tone(c, o, t + .02, { type: "square", f: 440, dur: .12, gain: .04 }); },
    rimshot: (c, o, t) => {
      tone(c, o, t, { f: 230, f2: 120, dur: .18, gain: .45 });
      tone(c, o, t + .17, { f: 170, f2: 85, dur: .2, gain: .45 });
      burst(c, o, t + .36, { filter: "bandpass", f: 1900, dur: .13, gain: .45 });
      burst(c, o, t + .36, { filter: "highpass", f: 6500, dur: .9, gain: .22 });
    },
  };

  // 길게 깔리는 소리
  const SPAN = {
    hum: (c, o, t0, t1) => {
      const g = c.createGain();
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(1, t0 + .35);
      g.gain.setValueAtTime(1, Math.max(t0 + .36, t1 - .3));
      g.gain.exponentialRampToValueAtTime(0.0001, t1);
      g.connect(o);
      [[120, .028], [240, .012], [360, .005]].forEach(([f, v]) => {
        const osc = c.createOscillator(), og = c.createGain();
        osc.frequency.value = f; og.gain.value = v; osc.connect(og); og.connect(g); osc.start(t0); osc.stop(t1 + .05);
      });
      const src = c.createBufferSource(), lp = c.createBiquadFilter(), ng = c.createGain();
      src.buffer = noise(c); src.loop = true; lp.type = "lowpass"; lp.frequency.value = 220; ng.gain.value = .03;
      src.connect(lp); lp.connect(ng); ng.connect(g); src.start(t0); src.stop(t1 + .05);
    },
    micro: (c, o, t0, t1) => {
      const g = c.createGain();
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(1, t0 + .15);
      g.gain.setValueAtTime(1, Math.max(t0 + .16, t1 - .05));
      g.gain.exponentialRampToValueAtTime(0.0001, t1);
      g.connect(o);
      const osc = c.createOscillator(), lp = c.createBiquadFilter(), og = c.createGain();
      osc.type = "sawtooth"; osc.frequency.value = 118; lp.type = "lowpass"; lp.frequency.value = 380; og.gain.value = .05;
      osc.connect(lp); lp.connect(og); og.connect(g); osc.start(t0); osc.stop(t1 + .05);
    },
  };

  // 배경음: 느린 C-Am-F-G 뜯는 소리 + 작은 킥·하이햇 (낮게)
  function bgm(c, o, t0, t1, from) {
    const beat = 60 / 88, bar = beat * 4;
    const chords = [[261.6, 329.6, 392], [220, 261.6, 329.6], [174.6, 220, 261.6], [196, 246.9, 293.7]];
    const startBar = Math.floor(from / bar);
    for (let b = startBar; b * bar < from + (t1 - t0) + bar; b++) {
      const ch = chords[b % 4];
      for (let k = 0; k < 8; k++) {
        const at = b * bar + k * beat / 2 - from;
        if (at < 0 || at > t1 - t0) continue;
        const f = ch[[0, 1, 2, 1, 0, 2, 1, 2][k]] * (k % 4 === 3 ? 2 : 1);
        tone(c, o, t0 + at, { type: "triangle", f, dur: .5, gain: .045, lp: 1600 });
        if (k % 4 === 0) tone(c, o, t0 + at, { f: 90, f2: 45, dur: .16, gain: .16 });
        if (k % 2 === 1) burst(c, o, t0 + at, { filter: "highpass", f: 7000, dur: .04, gain: .05 });
      }
    }
  }

  // 작품 → 효과음 계획 (영상 처음부터의 초)
  function plan(work) {
    const ev = [], spans = [];
    let at = 0, humFrom = null, microFrom = null;
    work.cuts.forEach((c) => {
      (c.sfx || []).forEach(([t, name]) => {
        const T = at + t;
        if (name === "hum_on") humFrom = T;
        else if (name === "hum_off") { if (humFrom !== null) spans.push({ name: "hum", from: humFrom, to: T }); humFrom = null; }
        else if (name === "micro") microFrom = T;
        else {
          if (name === "ding" && microFrom !== null) { spans.push({ name: "micro", from: microFrom, to: T }); microFrom = null; }
          ev.push({ t: T, name });
        }
      });
      at += c.dur;
    });
    if (humFrom !== null) spans.push({ name: "hum", from: humFrom, to: at });
    return { ev, spans, total: at };
  }

  // from(영상 초)부터 재생: base 는 ctx 시각
  function schedule(ctx, out, p, from, base, o = {}) {
    if (o.fx !== false) {
      p.ev.forEach((e) => { if (e.t >= from - .01 && FX[e.name]) FX[e.name](ctx, out, base + (e.t - from)); });
      p.spans.forEach((s) => { if (s.to > from) SPAN[s.name](ctx, out, base + Math.max(0, s.from - from), base + (s.to - from)); });
    }
    if (o.bgm) bgm(ctx, out, base, base + (p.total - from), from);
  }

  global.CCSound = { plan, schedule, FX };
})(window);
