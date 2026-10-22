/* 일정 알림 (2026-10-22 사용자): 일정 시각이 되면 우측 상단에 카드가 들어온다. 누르기 전까지 떠 있고,
   누르면 확인(ack)을 적고 오른쪽으로 들어간다. 모든 화면에서 20초마다 schedule:alarms 를 묻는다.
   다른 창에서 확인했으면 다음 물음 때 이 창에서도 들어간다. */
(function () {
  var cfg = window.APP || {};
  if (!cfg.alarmsUrl) return;
  var root = document.createElement("div");
  root.className = "alarm-root";
  root.setAttribute("aria-live", "assertive");
  document.body.appendChild(root);
  var shown = {};

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }

  function hide(el) {
    el.classList.remove("in");
    el.classList.add("out");
    setTimeout(function () { el.remove(); }, 300);
  }

  function show(a) {
    if (shown[a.id]) return;
    var el = document.createElement("button");
    el.type = "button";
    el.className = "alarm";
    el.title = "누르면 닫혀요";
    el.innerHTML = '<span class="alarm-k"><svg class="ic"><use href="#i-clock"/></svg>' + esc(a.time) + " 일정</span>" +
      '<span class="alarm-t">' + esc(a.title) + "</span>" + (a.note ? '<span class="alarm-n">' + esc(a.note) + "</span>" : "");
    el.addEventListener("click", function () {
      fetch(a.ack, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": cfg.csrfToken } });
      delete shown[a.id];
      hide(el);
    });
    shown[a.id] = el;
    root.appendChild(el);
    requestAnimationFrame(function () { requestAnimationFrame(function () { el.classList.add("in"); }); });
  }

  function poll() {
    fetch(cfg.alarmsUrl, { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d) return;
        var live = {};
        d.alarms.forEach(function (a) { live[a.id] = true; show(a); });
        Object.keys(shown).forEach(function (id) {
          if (!live[id]) { hide(shown[id]); delete shown[id]; }
        });
      })
      .catch(function () {});
  }

  poll();
  setInterval(poll, 20000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) poll(); });
})();
