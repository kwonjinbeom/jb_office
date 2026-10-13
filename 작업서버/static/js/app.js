/* 공통 스크립트: 사이드바 git 배지 갱신 + 홈 화면 git 패널 자동 갱신 (30초). */
(function () {
  "use strict";
  var cfg = window.APP || {};
  if (!cfg.gitStatusUrl) return;

  var INTERVAL_MS = 30000;

  function $(sel) { return document.querySelector(sel); }
  function all(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  function renderPill(data) {
    var dot = $('[data-git="dot"]');
    var branch = $('.gitpill [data-git="branch"]');
    var dirty = $('.gitpill [data-git="dirty"]');
    if (!dot) return;
    dot.className = "gitpill__dot " + (data.ok === false ? "is-error" : data.dirty ? "is-dirty" : "is-clean");
    if (branch) branch.textContent = data.branch || "?";
    if (dirty) {
      var parts = [];
      if (data.dirty) parts.push("±" + data.dirty);
      if (data.ahead) parts.push("↑" + data.ahead);
      if (data.behind) parts.push("↓" + data.behind);
      dirty.textContent = parts.join(" ");
    }
  }

  function renderHome(data) {
    var el;
    if ((el = $('.content [data-git="branch"]'))) el.textContent = data.branch || "?";
    if ((el = $('[data-git="dirty-value"]'))) {
      el.textContent = data.dirty;
      el.className = "stat__value " + (data.dirty ? "text-amber" : "text-green");
    }
    if ((el = $('[data-git="ahead"]'))) { el.textContent = data.ahead == null ? "-" : data.ahead; el.className = "stat__value " + (data.ahead ? "text-amber" : ""); }
    if ((el = $('[data-git="behind"]'))) { el.textContent = data.behind == null ? "-" : data.behind; el.className = "stat__value " + (data.behind ? "text-red" : ""); }
    if ((el = $('[data-git="checked_at"]'))) el.textContent = data.checked_at || "";

    if ((el = $('[data-git="changes"]'))) {
      var items = (data.changes || []).slice(0, 12).map(function (c) {
        var tone = (c.status || "?").charAt(0);
        return '<li><span class="filestatus filestatus--' + esc(tone) + '">' + esc(c.status) + '</span><span class="mono">' + esc(c.path) + "</span></li>";
      });
      if (!items.length) items.push('<li class="muted">작업 트리가 깨끗합니다.</li>');
      if ((data.changes || []).length > 12) items.push('<li class="muted">… 외 ' + (data.changes.length - 12) + "개</li>");
      el.innerHTML = items.join("");
    }
    if ((el = $('[data-git="commits"]'))) {
      el.innerHTML = (data.commits || []).map(function (c) {
        return "<tr><td class=\"mono\">" + esc(c.hash) + "</td><td>" + esc(c.subject) + '</td><td class="mono small muted">' + esc((c.date || "").slice(0, 16)) + "</td></tr>";
      }).join("");
    }
  }

  function refresh() {
    fetch(cfg.gitStatusUrl, { headers: { "X-Requested-With": "fetch" } })
      .then(function (r) { return r.json(); })
      .then(function (data) { renderPill(data); renderHome(data); })
      .catch(function () { renderPill({ ok: false, branch: "offline" }); });
  }

  refresh();
  setInterval(function () { if (!document.hidden) refresh(); }, INTERVAL_MS);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) refresh(); });

  // 삭제 버튼 같은 위험 동작은 폼이 confirm 페이지를 거치므로 별도 JS 는 없다.
})();
