/* memorily 애니 ↔ 만화 환산기. build.py 가 data/*.json 을 아래 __DATA__ 자리에 넣어 스킨에_붙일것.html 을 만든다.
   글 본문에 [환산기: naruto] 한 줄이 있으면 그 문단을 환산기로 바꾼다. 없으면 아무것도 하지 않는다.
   회차 한 칸 = [만화 첫 화, 만화 끝 화, 종류]  종류 1 원작 · 2 일부 원작 · 0 오리지널(만화 0) */
(function () {
  var DATA = __DATA__;
  var KIND = { 1: "원작", 2: "일부 원작", 0: "오리지널" };

  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    for (var k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (html != null) e.innerHTML = html;
    return e;
  }
  function volOf(work, ch) {
    var v = work.vols, n = 0;
    for (var i = 0; i < v.length; i++) if (v[i] <= ch) n = i + 1;
    return n;
  }
  function chText(work, a, b) {
    var va = volOf(work, a), vb = volOf(work, b);
    var c = a === b ? a + "화" : a + "~" + b + "화";
    var v = va === vb ? va + "권" : va + "~" + vb + "권";
    return { ch: "만화 " + c, vol: v };
  }
  function nearCanon(eps, i, step) {
    for (var j = i + step; j >= 0 && j < eps.length; j += step) if (eps[j][2]) return j;
    return -1;
  }
  // 시즌(기) 기준 → 전체 화수
  function absEp(s, season, ep) {
    if (!s.seasons || !season) return ep;
    return s.seasons[season - 1] + ep - 1;
  }
  function seasonOf(s, abs) {
    if (!s.seasons) return null;
    var n = 0;
    for (var i = 0; i < s.seasons.length; i++) if (s.seasons[i] <= abs) n = i + 1;
    return n ? n + "기 " + (abs - s.seasons[n - 1] + 1) + "화" : null;
  }
  function epLabel(s, abs) {
    var se = seasonOf(s, abs);
    return s.name + " " + abs + "화" + (se ? " (" + se + ")" : "");
  }

  function animeToManga(work, s, abs) {
    var eps = s.eps;
    if (!(abs >= 1 && abs <= eps.length)) return { big: "1~" + eps.length + "화 사이로 넣어 주세요" };
    var e = eps[abs - 1];
    if (e[2]) {
      var t = chText(work, e[0], e[1]);
      return { big: t.ch, tag: KIND[e[2]], sub: t.vol + " · " + epLabel(s, abs) };
    }
    var p = nearCanon(eps, abs - 1, -1), q = nearCanon(eps, abs - 1, 1), sub = [];
    if (p >= 0) sub.push("앞 원작 " + (p + 1) + "화 = 만화 " + eps[p][1] + "화");
    if (q >= 0) sub.push("다음 원작 " + (q + 1) + "화 = 만화 " + eps[q][0] + "화");
    return { big: "원작 없음", tag: "오리지널", sub: sub.join(" · ") };
  }

  function mangaToAnime(work, ch) {
    if (!(ch >= 1 && ch <= work.last)) return { big: "1~" + work.last + "화 사이로 넣어 주세요" };
    var hit = [];
    [1, 2].forEach(function (kind) {  // 원작 회차를 먼저, 없을 때만 일부 원작 회차 (오리지널 끝에 한 장면만 다시 나오는 화 때문)
      if (hit.length) return;
      work.series.forEach(function (s) {
        var first = 0, last = 0;
        s.eps.forEach(function (e, i) {
          if (e[2] === kind && e[0] <= ch && ch <= e[1]) { if (!first) first = i + 1; last = i + 1; }
        });
        if (first) hit.push({ s: s, a: first, b: last });
      });
    });
    var vol = volOf(work, ch) + "권";
    if (!hit.length) return { big: "애니에 없는 화", sub: "만화 " + ch + "화 · " + vol };
    var h = hit[0];
    var big = h.s.name + " " + (h.a === h.b ? h.a + "화" : h.a + "~" + h.b + "화");
    var se = seasonOf(h.s, h.a);
    return { big: big, from: h.s.name + " " + h.a + "화부터", sub: "만화 " + ch + "화 · " + vol + (se ? " · " + se : "") };
  }

  function build(box, work) {
    var root = el("div", { "class": "ac" });
    var tabs = el("div", { "class": "ac-tabs" });
    var t1 = el("button", { type: "button", "class": "on" }, "애니 → 만화");
    var t2 = el("button", { type: "button" }, "만화 → 애니");
    tabs.appendChild(t1); tabs.appendChild(t2);

    // 애니 → 만화: 시리즈 · (기) · 화
    var p1 = el("div", { "class": "ac-row" });
    var ser = el("select", { "aria-label": "시리즈" });
    work.series.forEach(function (s, i) { ser.appendChild(el("option", { value: i }, s.name + " (" + s.eps.length + "화)")); });
    var sea = el("select", { "aria-label": "기" });
    var ep = el("input", { type: "number", min: 1, inputmode: "numeric", placeholder: "화", "aria-label": "화" });
    p1.appendChild(ser); p1.appendChild(sea); p1.appendChild(ep);

    // 만화 → 애니: 화 · 권
    var p2 = el("div", { "class": "ac-row", hidden: "" });
    var unit = el("select", { "aria-label": "단위" });
    unit.appendChild(el("option", { value: "ch" }, "만화 화"));
    unit.appendChild(el("option", { value: "vol" }, "만화 권"));
    var num = el("input", { type: "number", min: 1, inputmode: "numeric", placeholder: "숫자", "aria-label": "숫자" });
    p2.appendChild(unit); p2.appendChild(num);

    var out = el("div", { "class": "ac-out" });
    root.appendChild(tabs); root.appendChild(p1); root.appendChild(p2); root.appendChild(out);

    function fillSeasons() {
      var s = work.series[ser.value];
      sea.innerHTML = "";
      sea.appendChild(el("option", { value: "" }, "전체 화수"));
      (s.seasons || []).forEach(function (_, i) { sea.appendChild(el("option", { value: i + 1 }, (i + 1) + "기")); });
      sea.hidden = !s.seasons;
      p1.className = "ac-row" + (s.seasons ? " ac-3" : "");
    }
    function show(r) {
      out.innerHTML = "";
      if (!r) { out.appendChild(el("div", { "class": "ac-sub" }, "숫자를 넣으면 바로 나옵니다")); return; }
      var big = el("div", { "class": "ac-big" }, r.big);
      if (r.tag) big.appendChild(el("span", { "class": "ac-tag" }, r.tag));
      out.appendChild(big);
      if (r.sub) out.appendChild(el("div", { "class": "ac-sub" }, r.sub));
    }
    function run() {
      if (!p1.hidden) {
        var s = work.series[ser.value], n = parseInt(ep.value, 10);
        if (!n) return show(null);
        var season = parseInt(sea.value, 10) || 0;
        if (season) {
          var size = (s.seasons[season] || s.eps.length + 1) - s.seasons[season - 1];
          if (n > size) return show({ big: season + "기는 " + size + "화까지 있어요" });
        }
        show(animeToManga(work, s, absEp(s, season, n)));
      } else {
        var m = parseInt(num.value, 10);
        if (!m) return show(null);
        if (unit.value === "vol") {
          if (m < 1 || m > work.vols.length) return show({ big: "1~" + work.vols.length + "권 사이로 넣어 주세요" });
          var a = work.vols[m - 1], b = m < work.vols.length ? work.vols[m] - 1 : work.last;
          var r = mangaToAnime(work, a);
          if (r.from) r.big = r.from;
          r.sub = m + "권 = 만화 " + a + "~" + b + "화";
          return show(r);
        }
        show(mangaToAnime(work, m));
      }
    }
    function tab(a) {
      t1.className = a ? "on" : ""; t2.className = a ? "" : "on";
      p1.hidden = !a; p2.hidden = a;
      run();
    }
    t1.onclick = function () { tab(true); };
    t2.onclick = function () { tab(false); };
    ser.onchange = function () { fillSeasons(); run(); };
    sea.onchange = ep.oninput = unit.onchange = num.oninput = run;
    fillSeasons(); show(null);
    box.parentNode.replaceChild(root, box);
  }

  function init() {
    var ps = document.querySelectorAll("p, div");
    for (var i = 0; i < ps.length; i++) {
      var m = /^\s*\[환산기:\s*([a-z0-9_-]+)\s*\]\s*$/.exec(ps[i].textContent);
      if (m && DATA[m[1]] && !ps[i].querySelector("p, div")) build(ps[i], DATA[m[1]]);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
