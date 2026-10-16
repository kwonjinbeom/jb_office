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

  // ---- 글 보기 폭 (티스토리 글쓰기)
  function setPaperWidth(mode) {
    var paper = document.getElementById("wr-paper");
    if (!paper) return;
    paper.classList.toggle("mobile", mode === "mobile");
    document.querySelectorAll("[data-paper-width]").forEach(function (b) {
      b.classList.toggle("on", b.getAttribute("data-paper-width") === mode);
    });
  }
  try { if (localStorage.getItem("wr.paperWidth") === "mobile") setPaperWidth("mobile"); } catch (err) {}

  // ---- 클릭
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      // 창에 초점이 없을 때 등 브라우저가 거절하면 예전 방식으로 한 번 더 시도한다.
      return navigator.clipboard.writeText(text).catch(function () { return copyTextBySelection(text); });
    }
    return copyTextBySelection(text);
  }

  function copyTextBySelection(text) {
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

  function copyRich(htmlText, plainText) {
    if (window.ClipboardItem && navigator.clipboard && navigator.clipboard.write && window.isSecureContext) {
      return navigator.clipboard.write([new ClipboardItem({
        "text/html": new Blob([htmlText], { type: "text/html" }),
        "text/plain": new Blob([plainText], { type: "text/plain" })
      })]).catch(function () { return copyRichBySelection(htmlText); });
    }
    return copyRichBySelection(htmlText);
  }

  // 예비: 화면 밖에 HTML 을 그려 놓고 선택해서 복사한다 (선택 영역 복사는 서식이 함께 간다).
  function copyRichBySelection(htmlText) {
    return new Promise(function (resolve, reject) {
      var box = document.createElement("div");
      box.innerHTML = htmlText;
      box.style.cssText = "position:fixed;left:-10000px;top:0;width:720px;background:#fff";
      document.body.appendChild(box);
      var range = document.createRange();
      range.selectNodeContents(box);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      try { document.execCommand("copy") ? resolve() : reject(); } catch (err) { reject(err); }
      sel.removeAllRanges();
      document.body.removeChild(box);
    });
  }

  document.addEventListener("click", function (e) {
    if (!e.target.closest) return;

    // 글 보기 폭: PC / 모바일. 고른 것은 이 브라우저에 기억한다.
    var pw = e.target.closest("[data-paper-width]");
    if (pw) {
      setPaperWidth(pw.getAttribute("data-paper-width"));
      try { localStorage.setItem("wr.paperWidth", pw.getAttribute("data-paper-width")); } catch (err) {}
      return;
    }

    // 토스트 닫기
    var x = e.target.closest(".toast .x");
    if (x) { hideToast(x.closest(".toast")); return; }

    // 서식 그대로 복사: data-copy-rich="#HTML원본" (+ data-copy-plain="#글원본").
    // 블로그 에디터에 붙여넣으면 소제목·굵게·표·상자 서식이 따라간다.
    var rich = e.target.closest("[data-copy-rich]");
    if (rich) {
      var hsrc = $(rich.getAttribute("data-copy-rich"));
      var psrc = $(rich.getAttribute("data-copy-plain") || "");
      if (hsrc) {
        copyRich(hsrc.value, psrc ? psrc.value : hsrc.value).then(
          function () { toast(rich.getAttribute("data-copy-msg") || "복사했습니다.", "ok"); },
          function () { toast("복사하지 못했습니다. 본문을 직접 드래그해 복사하세요.", "warn"); }
        );
      }
      return;
    }

    // 복사 버튼: data-copy="#입력칸" 의 값을 복사한다. data-copy-msg 가 있으면 그 문구로 알린다.
    var cp = e.target.closest("[data-copy]");
    if (cp) {
      var src = $(cp.getAttribute("data-copy"));
      if (src) {
        copyText(src.value != null ? src.value : src.textContent).then(
          function () { toast(cp.getAttribute("data-copy-msg") || "복사했습니다.", "ok"); },
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

  // 달력 띠 가운데 날짜를 누르면 오른쪽 날짜 칸의 캘린더를 연다.
  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest("[data-open-picker]");
    if (!btn) return;
    var input = btn.closest(".cal") && btn.closest(".cal").querySelector(".cal-tools input[type=date], .cal-tools input[type=month]");
    if (!input) return;
    try { input.showPicker(); } catch (err) { input.focus(); }
  });

  // 표 머리글의 '모두 선택' 체크박스: 같은 폼(form 속성)·같은 name 의 체크박스를 한꺼번에 켜고 끈다.
  document.addEventListener("change", function (e) {
    var all = e.target;
    if (!all.matches || !all.matches("input[data-check-all]")) return;
    var sel = 'input[type="checkbox"][name="' + all.getAttribute("data-check-all") + '"]';
    var formId = all.getAttribute("form");
    if (formId) sel += '[form="' + formId + '"]';
    document.querySelectorAll(sel).forEach(function (box) { box.checked = all.checked; });
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
    // 기간 '전체' 버튼: 같은 폼의 날짜 칸을 비우고 보낸다.
    var clear = e.target.closest && e.target.closest("[data-clear-dates]");
    if (clear && clear.form) {
      all('input[type="date"]').forEach(function (d) { if (d.form === clear.form) d.value = ""; });
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

  // 글 상자(data-autogrow)는 내용 길이에 맞춰 높이가 자란다.
  function autogrow(t) {
    t.style.height = "auto";
    t.style.height = (t.scrollHeight + 2) + "px";
  }
  all("textarea[data-autogrow]").forEach(autogrow);
  document.addEventListener("input", function (e) {
    if (e.target.matches && e.target.matches("textarea[data-autogrow]")) autogrow(e.target);
  });

  // 긴 글을 쓰는 폼(data-dirty-warn): 저장하지 않고 떠나려 하면 묻는다.
  all("form[data-dirty-warn]").forEach(function (form) {
    var dirty = false;
    form.addEventListener("input", function () { dirty = true; });
    form.addEventListener("submit", function () { dirty = false; });
    window.addEventListener("beforeunload", function (e) {
      if (!dirty) return;
      e.preventDefault();
      e.returnValue = "";
    });
  });

  // ---- 표 안의 접는 줄: data-toggle-row="#줄" (한 줄), data-toggle-rows=".줄들" (모두)
  function setRowOpen(row, open) {
    if (!row) return;
    row.hidden = !open;
    var button = document.querySelector('[data-toggle-row="#' + row.id + '"]');
    if (button) {
      button.setAttribute("aria-expanded", open ? "true" : "false");
      var owner = button.closest("tr");
      if (owner) owner.classList.toggle("open-row", open);
    }
    if (open) all("#" + row.id + " textarea[data-autogrow]").forEach(autogrow);
  }
  // 모두 펼치기/접기 버튼 하나: 다 열려 있으면 '모두 접기', 하나라도 닫혀 있으면 '모두 펼치기'
  function syncToggleAll() {
    all("[data-toggle-rows]").forEach(function (button) {
      var rows = all(button.getAttribute("data-toggle-rows"));
      var allOpen = rows.length > 0 && rows.every(function (r) { return !r.hidden; });
      button.setAttribute("aria-expanded", allOpen ? "true" : "false");
      var label = button.querySelector("[data-label]") || button;
      label.textContent = button.getAttribute(allOpen ? "data-label-close" : "data-label-open");
    });
  }
  document.addEventListener("click", function (e) {
    if (!e.target.closest) return;
    var one = e.target.closest("[data-toggle-row]");
    if (one) {
      var row = $(one.getAttribute("data-toggle-row"));
      var open = row && row.hidden;
      setRowOpen(row, open);
      syncToggleAll();
      if (open) { var box = row.querySelector("textarea, input[type=text]"); if (box) box.focus(); }
      return;
    }
    var many = e.target.closest("[data-toggle-rows]");
    if (many) {
      var rows = all(many.getAttribute("data-toggle-rows"));
      var openAll = rows.some(function (r) { return r.hidden; });
      rows.forEach(function (r) { setRowOpen(r, openAll); });
      syncToggleAll();
    }
  });

  // ---- 화면을 옮기지 않는 폼: form[data-ajax="log" | "adopt"]
  // 서버는 X-Requested-With: fetch 이면 JSON 으로 답한다 (apps/core/inplace.py). 실패하면 원래대로 제출한다.
  var AJAX_DONE = {
    log: function (form, data) {
      var panel = form.closest(".log-panel") || form.parentNode;
      var list = panel.querySelector("[data-log-list]");
      var empty = list && list.querySelector("[data-log-empty]");
      if (empty) empty.remove();
      if (list) {
        var li = document.createElement("li");
        li.className = "log fresh";
        li.dataset.trashModel = "ideas.idealog";
        li.dataset.trashId = data.log.id;
        li.dataset.trashTitle = data.log.body.slice(0, 200);
        li.innerHTML = '<div class="log-date"><b>' + esc(data.log.date.slice(5)) + "</b>" + esc(data.log.time) + "</div><div>" +
          (data.log.stage ? '<div class="log-meta">' + esc(data.log.stage) + "</div>" : "") +
          '<div class="log-body">' + esc(data.log.body).replace(/\n/g, "<br>") + "</div></div>";
        list.insertBefore(li, list.firstChild);
      }
      var row = form.closest("tr.log-row");
      var button = row && document.querySelector('[data-toggle-row="#' + row.id + '"]');
      if (button) {
        var n = button.querySelector("[data-log-count]");
        var d = button.querySelector(".d");
        if (n) n.textContent = data.count;
        if (d) d.textContent = data.log.date.slice(5);
      }
      var box = form.querySelector("textarea");
      if (box) { box.value = ""; autogrow(box); box.focus(); }
      toast("기록했습니다.", "ok");
    },
    adopt: function (form, data) {
      var link = document.createElement("a");
      link.className = "btn sm";
      link.href = data.url;
      link.innerHTML = '<svg class="ic"><use href="#i-check"/></svg>' + esc(data.code) + " 보기";
      form.replaceWith(link);
      var row = link.closest(".il-row");
      var meta = row && row.querySelector(".il-meta");
      if (meta && !meta.querySelector(".badge.green")) {
        meta.insertAdjacentHTML("beforeend", '<span class="badge green"><svg class="ic"><use href="#i-check"/></svg>' + esc(data.code) + " 담음</span>");
      }
      toast(data.message, "ok");
    },
  };
  document.addEventListener("submit", function (e) {
    var form = e.target;
    var kind = form.getAttribute && form.getAttribute("data-ajax");
    if (!kind || !AJAX_DONE[kind] || !window.fetch) return;
    e.preventDefault();
    if (form.dataset.busy) return;  // 보내는 중에 다시 눌러도 한 번만
    form.dataset.busy = "1";
    var buttons = all("button").filter(function (b) { return b.form === form; });
    buttons.forEach(function (b) { b.disabled = true; });
    fetch(form.action, { method: "POST", body: new FormData(form), headers: { "X-Requested-With": "fetch" }, credentials: "same-origin" })
      .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
      .then(function (res) {
        if (res.ok && res.data.ok) AJAX_DONE[kind](form, res.data);
        else toast(res.data.error || "저장하지 못했습니다.", "error");
      })
      .catch(function () { toast("연결이 끊겨 저장하지 못했습니다. 다시 눌러 주세요.", "error"); })
      .then(function () { delete form.dataset.busy; buttons.forEach(function (b) { b.disabled = false; }); });
  });
  // 짧은 기록 칸: Enter = 기록, Shift+Enter = 줄바꿈 (한글 조합 중에는 보내지 않는다)
  document.addEventListener("keydown", function (e) {
    var t = e.target;
    if (e.key !== "Enter" || e.shiftKey || e.ctrlKey || e.metaKey || e.isComposing || e.keyCode === 229) return;
    if (!t || t.tagName !== "TEXTAREA" || !t.form || t.form.getAttribute("data-ajax") !== "log") return;
    e.preventDefault();
    if (t.value.trim()) { if (t.form.requestSubmit) t.form.requestSubmit(); else t.form.submit(); }
  });

  // 주소 끝의 #idea-… · #logs-… 처럼 접힌 항목을 가리키면 펴서 보여 준다.
  if (location.hash.length > 1) {
    var target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (target && target.tagName === "DETAILS") { target.open = true; target.scrollIntoView({ block: "center" }); }
    if (target && target.classList.contains("log-row")) { setRowOpen(target, true); syncToggleAll(); target.scrollIntoView({ block: "center" }); }
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
