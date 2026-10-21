/* memorily 애니 ↔ 만화 환산기. build.py 가 data/*.json 을 아래 __DATA__ 자리에 넣어 스킨에_붙일것.html 을 만든다.
   글 본문에 [환산기: naruto] 한 줄이 있으면 그 문단을 환산기로 바꾼다. 없으면 아무것도 하지 않는다.
   회차 한 칸 = [만화 첫 화, 만화 끝 화, 종류]  종류 1 원작 · 2 원작 + 애니 장면 · 0 오리지널(만화 0)
   화면은 두 칸만 (2026-10-21 사용자: 기·권 칸까지 있으니 쓰기 어렵다): 애니 → 만화는 작품 + 화, 만화 → 애니는 화 하나. */
(function () {
  var DATA = __DATA__;
  // 글에 적힌 작품 이름을 넓게 받는다 (2026-10-22: 원피스 글이 [환산기: onpiece] 로 안 바뀌었다). 대소문자·빈칸 무시, 한글 이름·흔한 오타도
  var ALIAS = {"onpiece": "onepiece", "one-piece": "onepiece", "원피스": "onepiece", "나루토": "naruto", "블리치": "bleach",
               "헌터헌터": "hunterxhunter", "헌터x헌터": "hunterxhunter", "헌터×헌터": "hunterxhunter", "hxh": "hunterxhunter"};
  function keyOf(raw) {
    var k = String(raw).toLowerCase().replace(/\s+/g, "");
    k = ALIAS[k] || k;
    return DATA[k] ? k : "";
  }

  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    for (var k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (html != null) e.innerHTML = html;
    return e;
  }
  // 번호가 음수인 화(블리치 과거편 -108~-97화 등)는 작품 data 의 negvols [[처음, 끝, 권], ...] 로 권을 찾는다
  function volOf(work, ch) {
    if (ch < 0) {
      var hit = (work.negvols || []).filter(function (r) { return r[0] <= ch && ch <= r[1]; })[0];
      return hit ? hit[2] : 0;
    }
    if (work.volEnd && ch > work.volEnd) return 0;  // 연재 중인 작품: 최신권 다음 화는 아직 단행본에 없다
    var v = work.vols, n = 0;
    for (var i = 0; i < v.length; i++) if (v[i] <= ch) n = i + 1;
    return n;
  }
  function range(a, b) { return a === b ? a + "화" : a + "~" + b + "화"; }
  function volText(n) { return n ? n + "권" : "미수록"; }
  function vols(work, a, b) {
    var va = volOf(work, a), vb = volOf(work, b);
    return va === vb ? volText(va) : volText(va) + "~" + volText(vb);
  }

  // 이야기를 앞으로 나아가게 하는 원작 회차. 원작 + 애니 장면(2) 회차는 앞 원작보다 뒤이고 다음 원작을 앞지르지 않을 때만
  // (회상·앞당긴 장면만 있는 화를 빼려고)
  function nearCanon(eps, i, step) {
    var top = [], max = 0, k, nextStart = Infinity;
    for (k = eps.length - 1; k >= 0; k--) {
      top[k] = nextStart;
      if (eps[k][2] === 1) nextStart = eps[k][0];
    }
    for (k = 0; k < eps.length; k++) {
      var e = eps[k];
      top[k] = e[2] === 1 ? e[1] > max : e[2] === 2 && e[1] > max && e[1] <= top[k];
      if (e[2] === 1) max = Math.max(max, e[1]);
    }
    for (var j = i + step; j >= 0 && j < eps.length; j += step) if (top[j]) return j;
    return -1;
  }

  function animeToManga(work, s, n) {
    var eps = s.eps, next = work.series[work.series.indexOf(s) + 1];
    if (!(n >= 1 && n <= eps.length)) return { big: s.name + " 애니는 " + eps.length + "화까지 있어요" };
    var e = eps[n - 1];
    if (e[2]) {
      return {
        big: "만화 " + range(e[0], e[1]),
        sub: "단행본 " + vols(work, e[0], e[1]) + (e[2] === 2 ? " · 만화 내용에 애니 장면이 조금 더해진 화" : ""),
      };
    }
    var p = nearCanon(eps, n - 1, -1), q = nearCanon(eps, n - 1, 1), sub = [];
    if (p >= 0) sub.push("바로 앞 원작은 " + (p + 1) + "화 (만화 " + eps[p][1] + "화)");
    if (q >= 0) sub.push("다음 원작은 " + (q + 1) + "화 (만화 " + eps[q][0] + "화)");
    else if (next) sub.push("다음 원작은 " + next.name + " 1화 (만화 " + next.eps[0][0] + "화)");
    return { big: "만화에 없는 화 (애니 오리지널)", sub: sub.join(" · ") };
  }

  function mangaToAnime(work, ch) {
    if (!(ch >= 1 && ch <= work.last)) return { big: "만화는 " + work.last + "화까지 있어요" };
    // 그 화를 처음 다룬 회차부터 이어진 회차까지만 (한참 뒤 회상·오리지널 끝에 다시 나오는 장면은 뺀다)
    var hit = null;
    work.series.forEach(function (s) {
      if (hit) return;
      var first = 0, last = 0;
      s.eps.forEach(function (e, i) {
        if (!e[2] || e[0] > ch || ch > e[1]) return;
        if (!first) first = last = i + 1;
        else if (i + 1 - last <= 2) last = i + 1;
      });
      if (first) hit = { s: s, a: first, b: last };
    });
    var vol = "단행본 " + volText(volOf(work, ch));
    if (!hit) return { big: "애니로 안 나온 화", sub: vol };
    return { big: hit.s.name + " " + range(hit.a, hit.b), sub: vol };
  }

  function build(box, work) {
    var root = el("div", { "class": "ac" });
    var tabs = el("div", { "class": "ac-tabs" });
    var t1 = el("button", { type: "button", "class": "on" }, "애니 → 만화");
    var t2 = el("button", { type: "button" }, "만화 → 애니");
    tabs.appendChild(t1); tabs.appendChild(t2);

    var p1 = el("div", { "class": "ac-row" });
    var ser = el("select", { "aria-label": "작품" });
    work.series.forEach(function (s, i) { ser.appendChild(el("option", { value: i }, s.name)); });
    var ep = el("input", { type: "number", min: 1, inputmode: "numeric", "aria-label": "애니 몇 화" });
    function hint() { ep.placeholder = "1~" + work.series[ser.value].eps.length + "화"; }
    p1.appendChild(ser); p1.appendChild(ep);

    var p2 = el("div", { "class": "ac-row ac-1", hidden: "" });
    var num = el("input", { type: "number", min: 1, inputmode: "numeric", placeholder: "만화 1~" + work.last + "화", "aria-label": "만화 몇 화" });
    p2.appendChild(num);

    var out = el("div", { "class": "ac-out" });
    root.appendChild(tabs); root.appendChild(p1); root.appendChild(p2); root.appendChild(out);

    function show(r) {
      out.innerHTML = "";
      if (!r) { out.appendChild(el("div", { "class": "ac-sub" }, "화수를 넣으면 바로 나와요")); return; }
      out.appendChild(el("div", { "class": "ac-big" }, r.big));
      if (r.sub) out.appendChild(el("div", { "class": "ac-sub" }, r.sub));
    }
    function run() {
      if (!p1.hidden) {
        var n = parseInt(ep.value, 10);
        return show(n ? animeToManga(work, work.series[ser.value], n) : null);
      }
      var m = parseInt(num.value, 10);
      show(m ? mangaToAnime(work, m) : null);
    }
    function tab(a) {
      t1.className = a ? "on" : ""; t2.className = a ? "" : "on";
      p1.hidden = !a; p2.hidden = a;
      run();
    }
    t1.onclick = function () { tab(true); };
    t2.onclick = function () { tab(false); };
    ser.onchange = function () { hint(); run(); };
    ep.oninput = num.oninput = run;
    hint(); show(null);
    var article = box.closest("div.contents_style");  // 환산기 글에만 거는 표 칸 너비 (글모양.css)
    if (article) article.classList.add("ac-post");
    box.parentNode.replaceChild(root, box);
  }

  function init() {
    var ps = document.querySelectorAll("p, div");
    for (var i = 0; i < ps.length; i++) {
      var m = /^\s*\[\s*환산기\s*[:：]\s*([^\]]+?)\s*\]\s*$/.exec(ps[i].textContent);
      var key = m && keyOf(m[1]);
      if (key && !ps[i].querySelector("p, div")) build(ps[i], DATA[key]);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
