/* memorily 애니 ↔ 만화 환산기. build.py 가 아래 __DATA_URL__ 자리에 작품 데이터 주소를 넣어 스킨에_붙일것.html 을 만든다.
   글 본문에 [환산기: naruto] 한 줄이 있으면 데이터를 불러와 그 문단을 환산기로 바꾼다. 없으면 아무것도 하지 않는다.
   데이터는 스킨에 넣지 않고 저장소의 환산기데이터.json 을 읽는다 (2026-10-24: 작품을 더하고 스킨을 다시 안 붙여 강연금·히로아카·진격·귀멸이
   안 떴다). 그래서 작품을 더해도 main 에 push 만 하면 된다. 못 불러오면 [환산기: …] 줄을 그대로 둔다.
   회차 한 칸 = [만화 첫 화, 만화 끝 화, 종류]  종류 1 원작 · 2 원작 + 애니 장면 · 0 오리지널(만화 0)
   칸은 화수 하나만 (2026-10-21 사용자: 기·권 칸까지 있으니 쓰기 어렵다). 작품이 둘 이상이면 작품 칩을 더한다. */
(function () {
  var DATA_URL = "__DATA_URL__";
  var DATA = {};
  // 글에 적힌 작품 이름을 넓게 받는다 (2026-10-22: 원피스 글이 [환산기: onpiece] 로 안 바뀌었다). 대소문자·빈칸 무시.
  // 키 · 작품 이름(빈칸 빼고) · 작품 data 의 alias(줄임말 · 흔한 오타) 어느 것이든
  function norm(s) { return String(s).toLowerCase().replace(/\s+/g, ""); }
  function keyOf(raw) {
    var k = norm(raw);
    if (DATA[k]) return k;
    for (var key in DATA) {
      var w = DATA[key];
      if (norm(w.name) === k || (w.alias || []).map(norm).indexOf(k) >= 0) return key;
    }
    return "";
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
  // (회상·앞당긴 장면만 있는 화를 빼려고). 작품마다 한 번만 계산해 둔다.
  function forward(s) {
    if (s.fwd) return s.fwd;
    var eps = s.eps, top = [], max = 0, k, nextStart = Infinity;
    for (k = eps.length - 1; k >= 0; k--) {
      top[k] = nextStart;
      if (eps[k][2] === 1) nextStart = eps[k][0];
    }
    for (k = 0; k < eps.length; k++) {
      var e = eps[k];
      top[k] = e[2] === 1 ? e[1] > max : e[2] === 2 && e[1] > max && e[1] <= top[k];
      if (e[2] === 1) max = Math.max(max, e[1]);
    }
    return (s.fwd = top);
  }
  function nearCanon(s, i, step) {
    var top = forward(s);
    for (var j = i + step; j >= 0 && j < s.eps.length; j += step) if (top[j]) return j;
    return -1;
  }

  // 결과: big 큰 줄 · sub 작은 줄 · tag 이름표 [글, 색(ok 원작 · mix 원작+애니 · orig 오리지널 · none 없음)]
  function animeToManga(work, s, n) {
    var eps = s.eps, next = work.series[work.series.indexOf(s) + 1];
    if (!(n >= 1 && n <= eps.length)) return { big: s.name + " 애니는 " + eps.length + "화까지 있어요", tag: ["범위 밖", "none"] };
    var e = eps[n - 1];
    if (e[2]) {
      return {
        big: "만화 " + range(e[0], e[1]),
        sub: "단행본 " + vols(work, e[0], e[1]) + (e[2] === 2 ? " · 만화 내용에 애니 장면이 조금 더해진 화" : ""),
        tag: e[2] === 2 ? ["원작 + 애니 장면", "mix"] : ["원작", "ok"],
      };
    }
    var p = nearCanon(s, n - 1, -1), q = nearCanon(s, n - 1, 1), sub = [];
    if (p >= 0) sub.push("바로 앞 원작은 " + (p + 1) + "화 (만화 " + eps[p][1] + "화)");
    if (q >= 0) sub.push("다음 원작은 " + (q + 1) + "화 (만화 " + eps[q][0] + "화)");
    else if (next) sub.push("다음 원작은 " + next.name + " 1화 (만화 " + next.eps[0][0] + "화)");
    return { big: "만화에 없는 화", sub: sub.join(" · "), tag: ["애니 오리지널", "orig"] };
  }

  function mangaToAnime(work, ch) {
    if (!(ch >= 1 && ch <= work.last)) return { big: "만화는 " + work.last + "화까지 있어요", tag: ["범위 밖", "none"] };
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
    if (!hit) return { big: "애니로 안 나온 화", sub: vol, tag: ["애니 없음", "none"] };
    return { big: (work.series.length > 1 ? hit.s.name + " " : "애니 ") + range(hit.a, hit.b), sub: vol, tag: ["애니 방영", "ok"] };
  }

  // 화면 (2026-10-22 사용자: 구리타분하다 · 원피스는 고를 작품이 하나라 드롭다운이 필요 없다 · 펼치면 렉):
  // 위 방향 스위치 → (작품이 둘 이상이면) 작품 칩 → 큰 숫자 칸(− +) → 결과 카드. 고르기 상자·숫자 입력(type=number)은 쓰지 않는다.
  function build(box, work) {
    var root = el("div", { "class": "ac" });
    var head = el("div", { "class": "ac-head" });
    head.appendChild(el("div", { "class": "ac-title" }, work.name + " 화수 환산기"));
    var seg = el("div", { "class": "ac-seg", role: "tablist" });
    var t1 = el("button", { type: "button", "class": "on", role: "tab" }, "애니 → 만화");
    var t2 = el("button", { type: "button", role: "tab" }, "만화 → 애니");
    seg.appendChild(t1); seg.appendChild(t2); head.appendChild(seg);
    root.appendChild(head);

    var cur = 0, toManga = true;
    var chips = el("div", { "class": "ac-chips" });
    work.series.forEach(function (s, i) {
      var c = el("button", { type: "button", "class": "ac-chip" + (i ? "" : " on") }, s.name);
      c.onclick = function () {
        cur = i;
        [].forEach.call(chips.children, function (x, j) { x.className = "ac-chip" + (j === i ? " on" : ""); });
        clamp(); hint(); run(); input.focus();
      };
      chips.appendChild(c);
    });
    if (work.series.length > 1) root.appendChild(chips);

    var label = el("div", { "class": "ac-label" });
    var field = el("div", { "class": "ac-field" });
    var minus = el("button", { type: "button", "class": "ac-step", "aria-label": "한 화 앞" }, "−");
    var plus = el("button", { type: "button", "class": "ac-step", "aria-label": "한 화 뒤" }, "+");
    var input = el("input", { type: "text", inputmode: "numeric", autocomplete: "off", enterkeyhint: "done", "aria-label": "몇 화" });
    var unit = el("span", { "class": "ac-unit" }, "화");
    var wrap = el("div", { "class": "ac-num" });
    wrap.appendChild(input); wrap.appendChild(unit);
    field.appendChild(minus); field.appendChild(wrap); field.appendChild(plus);
    root.appendChild(label); root.appendChild(field);

    var out = el("div", { "class": "ac-out" });
    var tag = el("span", { "class": "ac-tag" }), big = el("div", { "class": "ac-big" }), sub = el("div", { "class": "ac-sub" });
    out.appendChild(tag); out.appendChild(big); out.appendChild(sub);
    root.appendChild(out);

    function max() { return toManga ? work.series[cur].eps.length : work.last; }
    function hint() {
      label.textContent = (toManga ? (work.series.length > 1 ? work.series[cur].name : "애니") : "만화") + " 몇 화인가요?";
      input.placeholder = "1~" + max();
    }
    function clamp() {
      var n = parseInt(input.value, 10);
      if (n > max()) input.value = max();
    }
    function show(r) {  // 칸은 그대로 두고 글만 바꾼다 (입력할 때마다 화면을 새로 만들지 않게)
      out.className = "ac-out" + (r ? "" : " empty");
      tag.textContent = r && r.tag ? r.tag[0] : "";
      tag.className = "ac-tag" + (r && r.tag ? " ac-" + r.tag[1] : "");
      big.textContent = r ? r.big : "화수를 넣으면 바로 나와요";
      sub.textContent = r && r.sub ? r.sub : (r ? "" : (toManga ? "애니 회차가 만화 몇 화인지" : "만화 화가 애니 몇 화인지") + " 알려 드려요");
    }
    function run() {
      var n = parseInt(input.value, 10);
      if (!n) return show(null);
      show(toManga ? animeToManga(work, work.series[cur], n) : mangaToAnime(work, n));
    }
    function step(d) {
      var n = (parseInt(input.value, 10) || 0) + d;
      input.value = Math.max(1, Math.min(max(), n));
      run();
    }
    function tab(a) {
      toManga = a;
      t1.className = a ? "on" : ""; t2.className = a ? "" : "on";
      chips.hidden = !a;
      input.value = "";
      hint(); run(); input.focus();
    }
    t1.onclick = function () { tab(true); };
    t2.onclick = function () { tab(false); };
    minus.onclick = function () { step(-1); };
    plus.onclick = function () { step(1); };
    input.oninput = function () {
      var v = input.value.replace(/[^0-9]/g, "").slice(0, 5);
      if (v !== input.value) input.value = v;
      run();
    };
    input.onkeydown = function (ev) {
      if (ev.key === "ArrowUp" || ev.key === "ArrowDown") { ev.preventDefault(); step(ev.key === "ArrowUp" ? 1 : -1); }
    };
    hint(); show(null);
    var article = box.closest("div.contents_style");  // 환산기 글에만 거는 표 칸 너비 (글모양.css)
    if (article) article.classList.add("ac-post");
    box.parentNode.replaceChild(root, box);
  }

  function init() {
    var ps = document.querySelectorAll("p, div"), found = [];
    for (var i = 0; i < ps.length; i++) {
      var m = /^\s*\[\s*환산기\s*[:：]\s*([^\]]+?)\s*\]\s*$/.exec(ps[i].textContent);
      if (m && !ps[i].querySelector("p, div")) found.push([ps[i], m[1]]);
    }
    if (!found.length || !window.fetch) return;
    fetch(DATA_URL).then(function (r) { return r.json(); }).then(function (d) {
      DATA = d;
      found.forEach(function (f) {
        var key = keyOf(f[1]);
        if (key) build(f[0], DATA[key]);
      });
    })["catch"](function () {});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
