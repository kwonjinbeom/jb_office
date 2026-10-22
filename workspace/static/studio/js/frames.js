/* 창작콘텐츠 › 판형 (2026-10-22). 같은 컷 그림을 인스타 카툰(4:5)과 숏폼(9:16) 판에 앉힌다. */
(function (D) {
  "use strict";
  const { clamp } = D.util;

  // 인스타 카툰 한 장 (1080×1350)
  D.slide = function (work, i, finish) {
    const cut = work.cuts[i], S = new D.Scene(1080, 1350, finish), soft = S.c.soft;
    if (i === 0) {
      S.text(cut.say.series || work.series, 540, 74, { size: 36, color: soft });
      S.text(cut.cap, 540, 182, { size: 98, lh: 1.18 });
      S.group({ x: -20, y: 250, s: 1.06 }, () => D.works[work.key].cuts[i](S, cut.say));
    } else {
      S.text(cut.cap, 540, 140, { size: 66, lh: 1.3 });
      S.group({ x: -27, y: 225, s: 1.05 }, () => D.works[work.key].cuts[i](S, cut.say));
    }
    S.text(`${i + 1}/${work.cuts.length}`, 1040, 1322, { size: 30, anchor: "end", color: soft });
    return S;
  };

  // 숏폼 시간표: 컷마다 시작 초
  D.timeline = function (work) {
    let at = 0;
    const out = work.cuts.map((c, i) => { const r = { i, start: at, dur: c.dur }; at += c.dur; return r; });
    return { cuts: out, total: at };
  };

  // 숏폼 한 장면 (1080×1920). t 는 영상 처음부터 지난 초
  D.short = function (work, t, finish) {
    const tl = D.timeline(work);
    const seg = tl.cuts.find((c) => t < c.start + c.dur) || tl.cuts[tl.cuts.length - 1];
    const lt = clamp(t - seg.start, 0, seg.dur), cut = work.cuts[seg.i];
    const S = new D.Scene(1080, 1920, finish, { t: lt, boil: Math.floor(t * 6) });
    // 자막: 한 글자씩 (초당 16자)
    const cap = seg.i === 0 && cut.hook ? cut.hook : cut.cap;
    const n = Math.ceil(clamp(lt / Math.max(.6, cap.replace(/\n/g, "").length / 16), 0, 1) * cap.length);
    const shown = cap.slice(0, n);
    if (shown) S.text(shown, 540, seg.i === 0 ? 400 : 390, { size: seg.i === 0 ? 84 : 76, lh: 1.3 });
    // 그림: 천천히 다가가고, 컷이 바뀔 때 살짝 튄다
    const enter = clamp(lt / .18, 0, 1);
    const zoom = 1.15 * (1 + .028 * (lt / seg.dur) + (1 - enter) * .035);
    S.group({ x: 0, y: 590, s: zoom, ox: 540, oy: 560 }, () => D.works[work.key].cuts[seg.i](S, cut.say));
    return { S, seg, lt };
  };
})(window.Doodle);
