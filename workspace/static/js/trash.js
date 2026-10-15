/* 모든 목록이 공유하는 작은 삭제 버튼, 선택 작업, 복원. */
(function () {
  "use strict";
  var cfg = window.APP || {};
  var dialog = document.getElementById("trash-dialog");
  if (!dialog || !window.fetch) return;
  var bar = document.querySelector(".trash-selection");
  var confirm = dialog.querySelector("[data-trash-confirm]");
  var description = dialog.querySelector("[data-trash-description]");
  var error = dialog.querySelector("[data-trash-error]");
  var pending = [], generation = 0, busy = false, opener = null;

  function svg(name) {
    var icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    icon.setAttribute("class", "ic");
    icon.setAttribute("aria-hidden", "true");
    var use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", "#i-" + name);
    icon.appendChild(use);
    return icon;
  }
  function button(label) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "trash-row-delete";
    b.title = label;
    b.setAttribute("aria-label", label);
    b.appendChild(svg("trash"));
    return b;
  }
  function recordData(record) {
    return { model: record.dataset.trashModel, id: record.dataset.trashId };
  }
  function post(url, data) {
    return fetch(url, { method: "POST", credentials: "same-origin", headers: {
      "Content-Type": "application/json", "X-CSRFToken": cfg.csrfToken,
      "X-Requested-With": "fetch"
    }, body: JSON.stringify(data) }).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok || !data.ok) throw new Error(data.error || "처리하지 못했어요. 다시 시도해 주세요.");
        return data;
      });
    });
  }

  function enhanceRecord(record) {
    if (record.dataset.trashReady) return;
    record.dataset.trashReady = "1";
    if (record.hasAttribute("data-trash-trigger")) return;
    record.classList.add("trash-record");
    var controls = document.createElement("span");
    controls.className = "trash-row-controls";
    var label = record.dataset.trashTitle || "항목";
    var check = record.querySelector('input[type="checkbox"][name="ids"]');
    if (!check) {
      check = document.createElement("input");
      check.type = "checkbox";
      check.setAttribute("aria-label", label + " 선택");
      controls.appendChild(check);
    }
    check.setAttribute("data-trash-select", "");
    check._trashRecord = record;
    var remove = button(label + " 삭제");
    remove.setAttribute("data-trash-single", "");
    remove._trashRecord = record;
    controls.appendChild(remove);
    if (record.tagName === "TR") {
      var table = record.closest("table");
      if (!table.dataset.trashEnhanced) {
        table.dataset.trashEnhanced = "1";
        table.classList.add("has-trash-controls");
        var head = table.querySelector("thead tr");
        if (head) {
          var th = document.createElement("th");
          th.className = "trash-action-cell";
          var headerLabel = document.createElement("span");
          headerLabel.className = "sr-only";
          headerLabel.textContent = "선택 및 삭제";
          th.appendChild(headerLabel);
          if (!head.querySelector('input[type="checkbox"]')) {
            var checkAll = document.createElement("input");
            checkAll.type = "checkbox";
            checkAll.setAttribute("data-trash-check-all", "");
            checkAll.setAttribute("aria-label", "모두 선택");
            th.appendChild(checkAll);
          }
          head.appendChild(th);
        }
        table.querySelectorAll("td[colspan]").forEach(function (td) { td.colSpan += 1; });
      }
      var cell = document.createElement("td");
      cell.className = "trash-action-cell";
      cell.appendChild(controls);
      record.appendChild(cell);
    } else if (record.tagName === "A") {
      var wrap = document.createElement("div");
      wrap.className = "trash-link-record";
      record.parentNode.insertBefore(wrap, record);
      wrap.appendChild(record);
      wrap.appendChild(controls);
    } else {
      var surface = record.tagName === "DETAILS" ? record.querySelector("summary") : record;
      if (surface) surface.appendChild(controls);
    }
    record.querySelectorAll('form[action$="/delete/"], a[href$="/delete/"]').forEach(function (old) { old.hidden = true; });
  }
  document.querySelectorAll("[data-trash-model][data-trash-id]").forEach(enhanceRecord);
  var body = document.querySelector(".page-body");
  if (body) new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      mutation.addedNodes.forEach(function (node) {
        if (node.nodeType !== 1) return;
        if (node.matches("[data-trash-model][data-trash-id]")) enhanceRecord(node);
        node.querySelectorAll("[data-trash-model][data-trash-id]").forEach(enhanceRecord);
      });
    });
  }).observe(body, {childList: true, subtree: true});

  function selected() {
    var unique = new Map();
    document.querySelectorAll("[data-trash-select]:checked").forEach(function (box) {
      var data = recordData(box._trashRecord);
      unique.set(data.model + ":" + data.id, data);
    });
    return Array.from(unique.values());
  }
  function restoreIds() {
    return Array.from(document.querySelectorAll("[data-trash-restore-check]:checked")).map(function (box) { return box.value; });
  }
  function syncSelection() {
    var ids = restoreIds(), count = ids.length || selected().length;
    bar.hidden = !count;
    bar.querySelector("[data-trash-selection-count]").textContent = count + "개 선택";
    bar.querySelector("[data-trash-bulk]").textContent = ids.length ? "선택 복원" : "선택 삭제";
    document.querySelectorAll("[data-trash-check-all]").forEach(function (all) {
      var scope = all.closest("table") || document;
      var boxes = Array.from(scope.querySelectorAll("[data-trash-select], [data-trash-restore-check]"));
      var n = boxes.filter(function (b) { return b.checked; }).length;
      all.checked = boxes.length > 0 && n === boxes.length;
      all.indeterminate = n > 0 && n < boxes.length;
    });
  }
  function showError(message) {
    error.textContent = message;
    error.hidden = false;
  }
  function openDelete(items, source) {
    if (busy) return;
    opener = source;
    pending = items;
    var ticket = ++generation;
    error.hidden = true;
    confirm.disabled = true;
    description.textContent = "연결된 항목을 확인하고 있어요…";
    dialog.querySelector("[data-trash-source-note]").hidden = true;
    dialog.showModal();
    post(cfg.trashPreviewUrl, {items: items}).then(function (data) {
      if (ticket !== generation || !dialog.open) return;
      description.textContent = (data.selected === 1 ? "‘" + data.title + "’" : data.selected + "개 항목") +
        (data.count > data.selected ? " 및 연결된 항목 " + (data.count - data.selected) + "개를 함께 이동해요." : "을(를) 이동해요.");
      dialog.querySelector("[data-trash-source-note]").hidden = !data.has_sources;
      confirm.disabled = false;
      dialog.querySelector("[data-trash-cancel]").focus();
    }).catch(function (err) { if (ticket === generation && dialog.open) showError(err.message); });
  }
  function flash(data, destination) {
    try { sessionStorage.setItem("office.trash.flash", JSON.stringify(data)); } catch (e) {}
    if (destination) location.assign(destination);
    else location.reload();
  }
  function doRestore(ids, control) {
    if (busy) return;
    busy = true;
    if (control) control.disabled = true;
    post(cfg.trashRestoreUrl, {ids: ids}).then(function (data) {
      flash({message: data.count + "개 항목을 복원했어요."});
    }).catch(function (err) {
      window.App.toast(err.message, "error");
      busy = false;
      if (control) control.disabled = false;
    });
  }
  confirm.addEventListener("click", function () {
    if (busy || confirm.disabled) return;
    busy = true;
    confirm.disabled = true;
    confirm.textContent = "이동 중…";
    post(cfg.trashMoveUrl, {items: pending}).then(function (data) {
      flash({message: data.count + "개 항목을 휴지통으로 이동했어요.", entries: data.entries},
        opener && opener.hasAttribute("data-trash-trigger") ? cfg.trashListUrl : null);
    }).catch(function (err) {
      showError(err.message);
      busy = false;
      confirm.disabled = false;
      confirm.textContent = "휴지통으로 이동";
    });
  });
  dialog.querySelector("[data-trash-cancel]").addEventListener("click", function () { dialog.close(); });
  dialog.addEventListener("close", function () { generation += 1; if (opener && opener.isConnected) opener.focus(); });
  document.addEventListener("change", function (event) {
    if (event.target.matches("[data-trash-check-all]")) {
      var scope = event.target.closest("table") || document;
      scope.querySelectorAll("[data-trash-select], [data-trash-restore-check]").forEach(function (box) { box.checked = event.target.checked; });
    }
    if (event.target.matches('[data-trash-select], [data-trash-restore-check], [data-trash-check-all], [data-check-all]')) syncSelection();
  });
  document.addEventListener("click", function (event) {
    var target = event.target.closest && event.target.closest("[data-trash-single], [data-trash-trigger], [data-trash-restore], [data-trash-bulk], [data-trash-clear], .trash-row-controls");
    if (!target) return;
    // A checkbox in a details summary must not toggle the details, but keep its native checked action.
    if (target.classList.contains("trash-row-controls")) { event.stopPropagation(); return; }
    event.preventDefault();
    event.stopPropagation();
    if (target.hasAttribute("data-trash-single")) openDelete([recordData(target._trashRecord)], target);
    else if (target.hasAttribute("data-trash-trigger")) openDelete([recordData(target)], target);
    else if (target.hasAttribute("data-trash-restore")) doRestore([target.dataset.trashRestore], target);
    else if (target.hasAttribute("data-trash-clear")) {
      document.querySelectorAll("[data-trash-select], [data-trash-restore-check], [data-check-all]").forEach(function (b) { b.checked = false; });
      syncSelection();
    } else if (target.hasAttribute("data-trash-bulk")) {
      var ids = restoreIds();
      if (ids.length) doRestore(ids, target);
      else openDelete(selected(), target);
    }
  }, true);
  try {
    var saved = JSON.parse(sessionStorage.getItem("office.trash.flash") || "null");
    sessionStorage.removeItem("office.trash.flash");
    if (saved && saved.message) {
      var notice = document.createElement("div");
      notice.className = "toast ok";
      notice.setAttribute("role", "status");
      var text = document.createElement("span");
      text.className = "tx";
      text.textContent = saved.message;
      notice.appendChild(text);
      if (saved.entries && saved.entries.length) {
        var undo = document.createElement("button");
        undo.className = "btn ghost sm";
        undo.textContent = "되돌리기";
        undo.addEventListener("click", function () { doRestore(saved.entries, undo); });
        notice.appendChild(undo);
      }
      document.getElementById("toast-root").appendChild(notice);
      setTimeout(function () { notice.remove(); }, 12000);
    }
  } catch (e) {}
  syncSelection();
})();
