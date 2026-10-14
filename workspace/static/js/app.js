/* 공통 스크립트: 토스트, 사이드바 git 상태 + 홈 Git 패널 자동 갱신(30초), 트리 메뉴, 행 클릭, 복사, 단축키(/ 검색, ← → 날짜). */
(function () {
  "use strict";
  var cfg = window.APP || {};

  function $(sel) { return document.querySelector(sel); }
  function all(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  // ---- 토스트: 서버 메시지(Django messages)와 화면 안 알림을 오른쪽 아래에 띄운다.
  var TOAST_ICON = { ok: "check-circle", error: "x-circle", warn: "alert", info: "info" };

  function hideToast(el) {
    el.classList.add("hide");
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 220);
  }
  function armToast(el) {
    // 오류·경고는 읽고 직접 닫을 때까지 둔다. 나머지는 글 길이에 맞춰 사라진다.
    if (el.classList.contains("error") || el.classList.contains("warn")) return;
    var ms = Math.min(10000, 3500 + el.textContent.trim().length * 45);
    setTimeout(function () { hideToast(el); }, ms);
  }
  function toast(msg, kind) {
    var root = $("#toast-root");
    if (!root) return;
    kind = TOAST_ICON[kind] ? kind : "info";
    var el = document.createElement("div");
    el.className = "toast " + kind;
    el.setAttribute("role", "status");
    el.innerHTML = '<svg class="ic"><use href="#i-' + TOAST_ICON[kind] + '"/></svg><span class="tx">' + esc(msg) + "</span>";
    root.appendChild(el);
    armToast(el);
  }
  window.App = { toast: toast, esc: esc };
  all("#toast-root .toast").forEach(armToast);

  // ---- git 상태
  var INTERVAL_MS = 30000;

  function renderPill(data) {
    var dot = $('#gitpill [data-git="dot"]');
    var branch = $('#gitpill [data-git="branch"]');
    var dirty = $('#gitpill [data-git="dirty"]');
    if (!dot) return;
    dot.className = "mk " + (data.ok === false ? "bad" : data.dirty ? "warn" : "ok");
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
    if ((el = $('.page-body [data-git="branch"]'))) el.textContent = data.branch || "?";
    if ((el = $('[data-git="dirty-value"]'))) { el.textContent = data.dirty; el.className = data.dirty ? "tone-warn" : "tone-ok"; }
    if ((el = $('[data-git="ahead"]'))) { el.textContent = data.ahead == null ? "-" : data.ahead; el.className = data.ahead ? "tone-warn" : ""; }
    if ((el = $('[data-git="behind"]'))) { el.textContent = data.behind == null ? "-" : data.behind; el.className = data.behind ? "tone-danger" : ""; }
    if ((el = $('[data-git="checked_at"]'))) el.textContent = data.checked_at || "";

    if ((el = $('[data-git="changes"]'))) {
      var items = (data.changes || []).slice(0, 12).map(function (c) {
        var tone = (c.status || "?").charAt(0);
        return '<li><span class="fstat" data-s="' + esc(tone) + '">' + esc(c.status) + '</span><span class="mono">' + esc(c.path) + "</span></li>";
      });
      if (!items.length) items.push('<li class="muted">작업 트리가 깨끗합니다.</li>');
      if ((data.changes || []).length > 12) items.push('<li class="muted">… 외 ' + (data.changes.length - 12) + "개</li>");
      el.innerHTML = items.join("");
    }
    if ((el = $('[data-git="commits"]'))) {
      el.innerHTML = (data.commits || []).map(function (c) {
        return '<tr><td class="mono small">' + esc(c.hash) + '</td><td title="' + esc(c.subject) + '">' + esc(c.subject) + '</td><td class="small muted num">' + esc((c.date || "").slice(0, 16)) + "</td></tr>";
      }).join("");
    }
  }

  function refresh() {
    fetch(cfg.gitStatusUrl, { headers: { "X-Requested-With": "fetch" } })
      .then(function (r) { return r.json(); })
      .then(function (data) { renderPill(data); renderHome(data); })
      .catch(function () { renderPill({ ok: false, branch: "offline" }); });
  }

  if (cfg.gitStatusUrl) {
    refresh();
    setInterval(function () { if (!document.hidden) refresh(); }, INTERVAL_MS);
    document.addEventListener("visibilitychange", function () { if (!document.hidden) refresh(); });
  }

  // ---- 클릭
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.cssText = "position:fixed;opacity:0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy") ? resolve() : reject(); } catch (e) { reject(e); }
      document.body.removeChild(ta);
    });
  }

  document.addEventListener("click", function (e) {
    if (!e.target.closest) return;

    // 토스트 닫기
    var x = e.target.closest(".toast .x");
    if (x) { hideToast(x.closest(".toast")); return; }

    // 복사 버튼: data-copy="#입력칸" 의 값을 복사한다.
    var cp = e.target.closest("[data-copy]");
    if (cp) {
      var src = $(cp.getAttribute("data-copy"));
      if (src) {
        copyText(src.value != null ? src.value : src.textContent).then(
          function () { toast("복사했습니다.", "ok"); },
          function () { src.select && src.select(); toast("복사하지 못했습니다. 직접 선택해 복사하세요.", "warn"); }
        );
      }
      return;
    }

    // 행 전체 클릭 → 상세. 행 안의 링크/버튼/폼을 눌렀을 때는 그 동작을 우선한다.
    var row = e.target.closest("tr[data-href]");
    if (!row) return;
    if (e.target.closest("a, button, input, form, select, label, summary")) return;
    if (String(window.getSelection && window.getSelection())) return;  // 글자를 긁는 중
    if (e.ctrlKey || e.metaKey) { window.open(row.getAttribute("data-href"), "_blank"); return; }
    window.location.href = row.getAttribute("data-href");
  });

  // ---- 입력 편의
  // 고르면 바로 적용되는 필터
  document.addEventListener("change", function (e) {
    var el = e.target;
    if (!el.matches || !el.matches("select[data-autosubmit], input[data-autosubmit]") || !el.form) return;
    if (el.tagName === "INPUT" && !el.value) return;  // 날짜를 지운 것은 이동이 아니다
    el.form.submit();
  });

  // 좌측 트리 메뉴: 화살표로 접었다 펴고, 편 것은 이 브라우저에 기억한다.
  var NAV_STORE = "nav.open";
  function navState() {
    try { return JSON.parse(localStorage.getItem(NAV_STORE) || "{}") || {}; } catch (err) { return {}; }
  }
  function setNavOpen(group, open) {
    group.classList.toggle("open", open);
    var caret = group.querySelector("[data-nav-toggle]");
    if (caret) caret.setAttribute("aria-expanded", open ? "true" : "false");
  }
  var saved = navState();
  all("[data-nav-group]").forEach(function (group) {
    // 현재 화면이 속한 가지는 서버가 이미 펴 두었다. 그 밖에는 기억해 둔 대로.
    if (!group.classList.contains("open") && saved[group.getAttribute("data-nav-group")]) setNavOpen(group, true);
  });
  document.addEventListener("click", function (e) {
    var caret = e.target.closest && e.target.closest("[data-nav-toggle]");
    if (caret) {
      var group = caret.closest("[data-nav-group]");
      var open = !group.classList.contains("open");
      setNavOpen(group, open);
      var state = navState();
      state[group.getAttribute("data-nav-group")] = open;
      try { localStorage.setItem(NAV_STORE, JSON.stringify(state)); } catch (err) { /* 저장 못 해도 동작은 한다 */ }
      return;
    }
    // 모두 펼치기 / 모두 접기: data-toggle-details="<details 선택자>"
    var toggle = e.target.closest && e.target.closest("[data-toggle-details]");
    if (toggle) {
      var rows = all(toggle.getAttribute("data-toggle-details"));
      var openAll = rows.some(function (d) { return !d.open; });
      rows.forEach(function (d) { d.open = openAll; });
      toggle.textContent = openAll ? toggle.getAttribute("data-label-close") : toggle.getAttribute("data-label-open");
    }
  });

  // 주소 끝의 #idea-… 처럼 접힌 항목을 가리키면 펴서 보여 준다.
  if (location.hash.length > 1) {
    var target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (target && target.tagName === "DETAILS") { target.open = true; target.scrollIntoView({ block: "center" }); }
  }

  document.addEventListener("keydown", function (e) {
    var t = e.target;
    var typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);

    // 글 상자에서 Ctrl+Enter → 저장
    if (t && t.tagName === "TEXTAREA" && e.key === "Enter" && (e.ctrlKey || e.metaKey) && t.form) {
      e.preventDefault();
      if (t.form.requestSubmit) t.form.requestSubmit(); else t.form.submit();
      return;
    }
    if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
    // "/" → 검색칸으로
    if (e.key === "/") {
      var box = $('.filter-bar input[type="search"], .il-filter input[type="search"]');
      if (box) { e.preventDefault(); box.focus(); box.select(); }
      return;
    }
    // 화면에 data-hotkey="ArrowLeft" 같은 링크가 있으면 그 키로 누른 것과 같다 (달력의 이전·다음 날).
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      var link = $('a[data-hotkey="' + e.key + '"]');
      if (link) { e.preventDefault(); link.click(); }
    }
  });

  // 좁은 화면의 가로 메뉴에서 현재 메뉴가 보이게 한다.
  var active = $(".nav .nav-item.active");
  if (active && active.scrollIntoView && window.matchMedia("(max-width: 760px)").matches) {
    active.scrollIntoView({ block: "nearest", inline: "center" });
  }

  // 삭제 같은 위험 동작은 폼이 confirm 페이지를 거치므로 별도 JS 는 없다.
})();
