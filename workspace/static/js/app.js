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

    // 글 그대로 복사: data-copy-text="글". 누른 버튼은 .done 으로 표시한다 (네이버 태그를 하나씩 넣을 때 어디까지 했는지).
    var ct = e.target.closest("[data-copy-text]");
    if (ct) {
      copyText(ct.getAttribute("data-copy-text")).then(
        function () { ct.classList.add("done"); toast(ct.getAttribute("data-copy-msg") || "복사했습니다.", "ok"); },
        function () { toast("복사하지 못했습니다.", "warn"); }
      );
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
    if (el.tagName === "INPUT" && el.type !== "number" && !el.value && !el.hasAttribute("data-allow-empty")) return;  // 날짜를 지운 것은 이동이 아니다 (숫자 칸을 비우면 자동 값으로, 발행 예정일은 지우기)
    if (el.type === "date" && el.value && el.value.slice(0, 4) < "2000") return;  // 연도를 치는 중 (0002-…)
    el.form.submit();
  });

  // 달력 띠 가운데 날짜를 누르면 그 자리(바로 아래)에 캘린더를 연다. 입력칸은 .cal-pick 안에 숨어 있다.
  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest("[data-open-picker]");
    if (!btn) return;
    var input = btn.parentNode.querySelector(".cal-pick-input");
    if (!input) return;
    try { input.showPicker(); } catch (err) { input.focus(); }
  });

  // 일일루틴 '실행': 안내문을 클립보드에 복사하고 jbroutine: 링크로 PC 에서 claude 터미널을 연다 (PC 서버 없이).
  // 링크는 PC 에서 workspace\run.bat(또는 routine_link.bat)을 한 번 실행하면 등록된다 (apps/routines/local_run.py).
  // 글쓰기 '추가로 쓰기'도 서버에서 안내문을 받은 뒤 같은 방법으로 연다 (App.rtLaunch, templates/routines/index.html).
  function rtLaunch(prompt, f, reload) {
    var q = new URLSearchParams({ key: f.key, day: f.day, name: f.name || "" });
    if (f.keys) q.set("keys", f.keys);
    var link = "jbroutine:" + (f.kind || "run") + "?" + q.toString();
    copyText(prompt).then(
      function () {
        window.location.href = link;
        toast(f.msg || "PC 터미널에서 claude 를 엽니다. 안 열리면 PC 에서 workspace\\routine_link.bat 을 한 번 실행하세요.", "ok");
        if (reload) setTimeout(function () { location.reload(); }, 4000);
      },
      function () { toast("안내문을 복사하지 못했습니다. 다시 눌러 보세요.", "warn"); }
    );
  }
  window.App.rtLaunch = rtLaunch;
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form.matches || !form.matches("form.rt-launch")) return;
    e.preventDefault();
    var field = function (n) { var el = form.elements.namedItem(n); return el ? el.value : ""; };
    rtLaunch(field("prompt"), { kind: field("kind"), key: field("key"), day: field("day"), name: field("name"), keys: field("keys") },
             form.hasAttribute("data-reload"));
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
  // 왼쪽 메뉴 접기: 아이콘만 남긴다. 처음 그릴 때의 접힘은 <head> 의 짧은 스크립트가 먼저 붙인다.
  var root = document.documentElement;
  function setMini(mini) {
    root.classList.toggle("nav-mini", mini);
    all("[data-nav-mini]").forEach(function (b) {
      b.setAttribute("aria-expanded", mini ? "false" : "true");
      b.title = mini ? "메뉴 펼치기" : "메뉴 접기";
    });
    try { localStorage.setItem("nav.mini", mini ? "1" : "0"); } catch (err) { /* 기억 못 해도 동작은 한다 */ }
  }
  if (root.classList.contains("nav-mini")) setMini(true);
  document.addEventListener("click", function (e) {
    if (e.target.closest && e.target.closest("[data-nav-mini]")) { setMini(!root.classList.contains("nav-mini")); return; }
    var caret = e.target.closest && e.target.closest("[data-nav-toggle]");
    if (caret && root.classList.contains("nav-mini") && window.matchMedia("(min-width: 761px)").matches) {
      // 접힌 메뉴에서 하위 메뉴가 있는 항목을 누르면 메뉴를 펴고 그 가지를 연다
      setMini(false);
      if (!caret.closest("[data-nav-group]").classList.contains("open")) caret.click();
      return;
    }
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

/* 변환 (2026-10-22 사용자: 사이트별 템플릿의 변환을 글 관리로).
   - 칸 펼치기: <button data-cv-open="주소" data-cv-target="#상자"> 는 그 상자에 변환 칸(원문 ↔ 변환본)을 받아 넣는다 (글 상세 화면).
   - 넣은 곳 고르기: 칸 안의 data-cv-tab 은 그 칸만 다시 받는다.
   - 변환: data-st-run="매핑 번호,…" (+ data-st-url, data-st-count) → 서버가 변환 요청으로 바꾸고 안내문을 주면 PC 터미널 claude 를 연다. */
(function () {
  function load(box, url) {
    box.innerHTML = '<div class="cv-loading muted small">변환 칸을 여는 중…</div>';
    fetch(url, { credentials: "same-origin" }).then(function (r) { return r.text(); })
      .then(function (html) { box.innerHTML = html; })
      .catch(function () { box.innerHTML = '<div class="muted small">열지 못했습니다. 다시 눌러 보세요.</div>'; });
  }
  document.addEventListener("click", function (e) {
    var tab = e.target.closest("[data-cv-tab]");
    if (tab) { load(tab.closest("[data-cv-panel-box]").parentNode, tab.getAttribute("data-cv-tab")); return; }
    var open = e.target.closest("[data-cv-open]");
    if (open) {
      var target = document.querySelector(open.getAttribute("data-cv-target"));
      if (!target) return;
      if (!target.hidden && target.childElementCount) { target.hidden = true; open.setAttribute("aria-expanded", "false"); return; }
      target.hidden = false; open.setAttribute("aria-expanded", "true");
      load(target, open.getAttribute("data-cv-open"));
    }
  });

  // 재변환: 체크한 글 하나 + 코멘트 → 지난 변환본을 코멘트대로 고친다 (글 관리 발행예정글 위 줄)
  document.addEventListener("click", function (e) {
    var rc = e.target.closest("[data-reconvert]");
    if (!rc || rc.disabled) return;
    var boxes = document.querySelectorAll('input[name="ids"]:checked');
    if (boxes.length !== 1) { window.App.toast("재변환은 한 건씩: 글 하나만 체크하세요.", "warn"); return; }
    var note = document.getElementById("rc-note");
    if (!note || !note.value.trim()) { window.App.toast("무엇을 고칠지 코멘트를 적으세요.", "warn"); if (note) note.focus(); return; }
    var data = new FormData();
    data.set("csrfmiddlewaretoken", (window.APP || {}).csrfToken || "");
    data.set("p", boxes[0].value);
    data.set("note", note.value);
    rc.disabled = true;
    fetch(rc.getAttribute("data-url"), { method: "POST", body: data, credentials: "same-origin" })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        rc.disabled = false;
        if (!res.ok) { window.App.toast(res.j.error || "안내문을 만들지 못했습니다.", "warn"); return; }
        note.value = "";
        window.App.rtLaunch(res.j.prompt, { kind: "convert", key: res.j.key, day: res.j.day, name: "재변환" }, true);
      })
      .catch(function () { rc.disabled = false; window.App.toast("안내문을 만들지 못했습니다. 다시 눌러 보세요.", "warn"); });
  });

  document.addEventListener("click", function (e) {
    var go = e.target.closest("[data-st-run]");
    if (!go || go.disabled) return;
    var n = Number(go.getAttribute("data-st-count") || 0);
    if (n > 1 && !confirm(n + "편을 변환합니다. PC 터미널에서 claude 가 차례로 변환해 서버로 보냅니다.")) return;
    var data = new FormData();
    data.set("csrfmiddlewaretoken", (window.APP || {}).csrfToken || "");
    data.set("ids", go.getAttribute("data-st-run"));
    go.disabled = true;
    fetch(go.getAttribute("data-st-url") || "/blog/site-templates/run/", { method: "POST", body: data, credentials: "same-origin" })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { window.App.toast(res.j.error || "안내문을 만들지 못했습니다.", "warn"); go.disabled = false; return; }
        window.App.rtLaunch(res.j.prompt, { kind: "convert", key: res.j.key, day: res.j.day, name: "사이트 변환" }, true);
      })
      .catch(function () { window.App.toast("안내문을 만들지 못했습니다. 다시 눌러 보세요.", "warn"); go.disabled = false; });
  });
})();

/* 모니터링 '발행 확인' (2026-10-22 사용자): 서버는 티스토리·네이버에 못 나가서 PC 가 RSS 를 읽는다.
   안내(JSON)를 받아 jbroutine:feeds 로 PC 를 깨우고, 서버의 마지막 확인 시각이 바뀌면 새로고침한다 (최대 2분). */
(function () {
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-feeds-check]");
    if (!btn || btn.disabled) return;
    btn.disabled = true;
    var body = new FormData();
    body.append("csrfmiddlewaretoken", window.APP.csrfToken);
    var statusUrl = btn.getAttribute("data-status"), before = null;
    fetch(statusUrl, { credentials: "same-origin" }).then(function (r) { return r.json(); })
      .then(function (j) { before = j.checked_at; })
      .then(function () { return fetch(btn.getAttribute("data-url"), { method: "POST", body: body, credentials: "same-origin" }); })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok) { btn.disabled = false; window.App.toast(res.j.error || "발행 확인을 시작하지 못했습니다.", "warn"); return; }
        window.App.rtLaunch(res.j.prompt, { kind: "feeds", key: res.j.key, day: res.j.day, name: "발행 확인",
          msg: "PC 에서 사이트마다 RSS 를 읽습니다. 끝나면 이 화면이 새로고침됩니다." }, false);
        var tries = 0, timer = setInterval(function () {
          tries += 1;
          fetch(statusUrl, { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(function (j) {
            if (j.checked_at && j.checked_at !== before) { clearInterval(timer); location.reload(); }
          });
          if (tries >= 40) { clearInterval(timer); btn.disabled = false; window.App.toast("아직 결과가 없습니다. PC 창의 안내를 확인하세요.", "warn"); }
        }, 3000);
      })
      .catch(function () { btn.disabled = false; window.App.toast("발행 확인을 시작하지 못했습니다. 다시 눌러 보세요.", "warn"); });
  });
})();
