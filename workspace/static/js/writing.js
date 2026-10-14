(function () {
  "use strict";
  var root = document.getElementById("wr-root");
  if (!root) return;
  var form = document.getElementById("wr-form"),
    body = document.getElementById("id_body");
  var bundle = JSON.parse(document.getElementById("wr-bundle").textContent);
  var state = document.getElementById("wr-save-state"),
    error = document.getElementById("wr-error");
  var sources = bundle.values.sources || [],
    timer,
    inFlight,
    dirty = false,
    serial = 0,
    busy = false;
  var storagePrefix = "jb-writing-draft-" + root.dataset.id;
  var storageKey =
    storagePrefix +
    "-" +
    (window.crypto && crypto.randomUUID
      ? crypto.randomUUID()
      : Date.now() + "-" + Math.random());
  var savedFingerprint,
    recovered,
    recoveredKey,
    recoveryToClear = [];
  function clearOwnBackup() {
    try {
      localStorage.removeItem(storageKey);
      recoveryToClear.forEach(function (key) {
        localStorage.removeItem(key);
      });
      recoveryToClear = [];
    } catch (_) {}
  }
  function field(name) {
    return form.elements.namedItem(name);
  }
  function text(node, value) {
    node.textContent = value;
  }
  function showError(message) {
    text(error, message);
    error.hidden = false;
  }
  function clearError() {
    error.hidden = true;
  }
  function fingerprint() {
    return JSON.stringify(
      Array.from(new FormData(form).entries()).filter(function (entry) {
        return !["csrfmiddlewaretoken", "revision", "signature"].includes(
          entry[0],
        );
      }),
    );
  }
  function browserBackup() {
    var values = {};
    new FormData(form).forEach(function (value, name) {
      if (["csrfmiddlewaretoken", "signature", "revision"].includes(name))
        return;
      if (name === "checks") {
        (values.checks || (values.checks = [])).push(value);
      } else values[name] = value;
    });
    values.checks = values.checks || [];
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify({
          values: values,
          signature: bundle.signature,
          updated: Date.now(),
        }),
      );
    } catch (_) {
      return false;
    }
    return true;
  }
  function localBackupDownload() {
    var draftValues = {};
    [
      "template_key",
      "keyword",
      "tags",
      "question",
      "answer",
      "experience",
      "description",
      "published_url",
    ].forEach(function (name) {
      draftValues[name] = field(name).value;
    });
    draftValues.profile_id = Number(field("profile").value) || null;
    draftValues.commercial = field("commercial").checked;
    draftValues.sources = sources;
    draftValues.checks = Array.from(
      form.querySelectorAll('input[name="checks"]:checked'),
    ).map(function (input) {
      return input.value;
    });
    var backup = {
      content: {
        title: field("title").value,
        body: body.value,
        status: field("status").value,
        summary: field("answer").value.slice(0, 140),
        folder_id: Number(field("folder").value) || null,
      },
      draft: draftValues,
      published_on: field("published_on").value,
    };
    var url = URL.createObjectURL(
      new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" }),
    );
    var link = document.createElement("a");
    link.href = url;
    link.download = "tistory-" + root.dataset.id + "-editing.json";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 1000);
  }
  function manualCount() {
    text(
      document.getElementById("wr-manual-count"),
      form.querySelectorAll('input[name="checks"]:checked').length + " / 5",
    );
  }
  function changed(resetChecks) {
    serial += 1;
    if (resetChecks)
      form.querySelectorAll('input[name="checks"]').forEach(function (input) {
        input.checked = false;
      });
    dirty = fingerprint() !== savedFingerprint;
    text(state, dirty ? "저장 대기" : "저장됨");
    state.classList.toggle("pending", dirty);
    manualCount();
    text(
      document.getElementById("wr-count"),
      body.value.replace(/\s/g, "").length.toLocaleString() + "자",
    );
    if (dirty) browserBackup();
    clearTimeout(timer);
    if (dirty && !busy)
      timer = setTimeout(function () {
        save(true).catch(function () {});
      }, 1800);
  }
  function applyValues(values) {
    Object.keys(values).forEach(function (name) {
      if (["profile_id", "sources", "checks"].includes(name)) return;
      var input = field(name);
      if (!input) return;
      if (input.type === "checkbox") input.checked = Boolean(values[name]);
      else input.value = values[name] == null ? "" : values[name];
    });
    form.querySelectorAll('input[name="checks"]').forEach(function (input) {
      input.checked = (values.checks || []).includes(input.value);
    });
    sources = values.sources || [];
    if (typeof sources === "string") {
      try {
        sources = JSON.parse(sources);
      } catch (_) {
        sources = [];
      }
    }
    renderSources();
  }
  function escape(value) {
    return String(value).replace(/[&<>"']/g, function (c) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[c];
    });
  }
  function render(data) {
    text(document.getElementById("wr-transfer-title"), field("title").value);
    text(
      document.getElementById("wr-count"),
      data.analysis.chars.toLocaleString() + "자",
    );
    var panel = document.getElementById("wr-analysis");
    panel.replaceChildren();
    data.analysis.checks.forEach(function (item) {
      var row = document.createElement("div"),
        label = document.createElement("strong"),
        detail = document.createElement("p");
      row.className = "wr-check-result " + (item.ok ? "ok" : "warn");
      text(label, (item.ok ? "✓ " : "· ") + item.label);
      text(detail, item.detail);
      row.append(label, detail);
      panel.append(row);
    });
    var preview = document.getElementById("wr-preview");
    preview.srcdoc =
      '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><style>body{font-family:system-ui,sans-serif;color:#273142;line-height:1.85;padding:28px;max-width:760px;margin:auto;overflow-wrap:anywhere}h1{font-size:26px;line-height:1.4}h2{font-size:22px;margin-top:32px}h3{font-size:19px}p{margin:14px 0}a{color:#2f6bd8}table{width:100%;border-collapse:collapse;display:block;overflow:auto}td,th{border:1px solid #dce2ea;padding:8px;text-align:left}th{background:#f5f7fa}img{max-width:100%;height:auto}blockquote{border-left:3px solid #8caee8;margin:20px 0;padding:8px 16px;background:#f6f8fc}pre{overflow:auto;background:#f5f7fa;padding:12px}code{font-family:monospace}</style><body><h1>' +
      escape(field("title").value) +
      "</h1>" +
      data.html +
      "</body></html>";
    var titles = document.getElementById("wr-titles");
    titles.replaceChildren();
    data.titles.forEach(function (title) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "wr-title-choice";
      text(button, title);
      button.addEventListener("click", function () {
        field("title").value = title.slice(0, 160);
        changed(true);
        text(
          document.getElementById("wr-transfer-title"),
          field("title").value,
        );
      });
      titles.append(button);
    });
    var versions = document.getElementById("wr-version-list");
    if (versions && data.versions) {
      versions.replaceChildren();
      text(document.getElementById("wr-version-count"), data.versions.length);
      data.versions.forEach(function (version) {
        var row = document.createElement("div"),
          label = document.createElement("span"),
          button = document.createElement("button");
        row.className = "wr-version";
        label.className = "small";
        text(label, version.time + " · " + version.label);
        button.className = "btn sm";
        button.type = "button";
        text(button, "복구");
        button.addEventListener("click", function () {
          perform("restore", { version: version.id });
        });
        row.append(label, button);
        versions.append(row);
      });
      if (!data.versions.length) {
        var empty = document.createElement("p");
        empty.className = "muted small";
        text(empty, "저장·구성 만들기·AI 생성 전 상태를 최대 30개 보관합니다.");
        versions.append(empty);
      }
    }
    manualCount();
  }
  async function request(url, data) {
    var response;
    try {
      response = await fetch(url, {
        method: "POST",
        body: data,
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
    } catch (_) {
      throw new Error(
        "서버 연결에 실패했습니다. 편집 내용은 이 브라우저에 보관합니다.",
      );
    }
    if (response.redirected)
      throw new Error(
        "로그인 상태를 확인하세요. 편집 내용을 보관한 뒤 다시 로그인하세요.",
      );
    var result;
    try {
      result = await response.json();
    } catch (_) {
      throw new Error(
        "서버 응답을 읽지 못했습니다. 원고를 복사·다운로드해 보관하세요.",
      );
    }
    if (!response.ok) {
      var details = [];
      if (result.errors)
        Object.keys(result.errors).forEach(function (key) {
          result.errors[key].forEach(function (item) {
            details.push(item.message);
          });
        });
      if (result.generated)
        fallback("AI 생성 결과 · 현재 원고는 유지", result.generated.body);
      throw new Error(
        [result.error || "요청을 처리하지 못했습니다."]
          .concat(details)
          .join(" "),
      );
    }
    return result;
  }
  async function save(automatic) {
    clearTimeout(timer);
    if (busy) throw new Error("작성 도구가 작업 중입니다. 잠시 기다려 주세요.");
    if (inFlight) {
      await inFlight;
      return dirty ? save(automatic) : bundle;
    }
    if (!dirty) return bundle;
    var started = serial,
      posted = new FormData(form);
    if (automatic) posted.append("autosave", "1");
    text(state, "저장 중…");
    inFlight = (async function () {
      try {
        var result = await request(root.dataset.save, posted);
        field("revision").value = result.revision;
        field("signature").value = result.signature;
        bundle = result;
        if (serial === started) {
          form
            .querySelectorAll('input[name="checks"]')
            .forEach(function (input) {
              input.checked = result.values.checks.includes(input.value);
            });
          [
            "title",
            "tags",
            "status",
            "answer",
            "description",
            "keyword",
          ].forEach(function (name) {
            field(name).value = result.values[name];
          });
          savedFingerprint = fingerprint();
          dirty = false;
          clearOwnBackup();
          clearError();
          text(state, result.saved_at + " 저장됨");
          state.classList.remove("pending");
        } else {
          dirty = true;
          browserBackup();
          text(state, "추가 변경 저장 대기");
        }
        render(result);
        return result;
      } catch (exc) {
        text(state, "저장하지 못함");
        var backed = browserBackup();
        showError(
          exc.message +
            (backed
              ? ""
              : " 브라우저 복구 저장도 사용할 수 없습니다. 현재 편집 백업을 내려받아 보관하세요."),
        );
        throw exc;
      } finally {
        inFlight = null;
      }
    })();
    var result = await inFlight;
    if (dirty) return save(automatic);
    return result;
  }
  function serializeSources() {
    field("sources").value = JSON.stringify(sources);
  }
  function renderSources() {
    var container = document.getElementById("wr-sources");
    container.replaceChildren();
    sources.forEach(function (source, index) {
      var row = document.createElement("div");
      row.className = "wr-source";
      var top = document.createElement("div");
      top.className = "wr-inline";
      var title = document.createElement("strong");
      text(title, "자료 " + (index + 1));
      var remove = document.createElement("button");
      remove.type = "button";
      remove.className = "btn ghost danger sm";
      text(remove, "삭제");
      remove.addEventListener("click", function () {
        sources.splice(index, 1);
        renderSources();
        changed(true);
      });
      top.append(title, remove);
      row.append(top);
      [
        ["title", "자료 이름", "text", 180],
        ["url", "원문 주소 (직접 경험이면 생략)", "url", 600],
        ["note", "글에 사용할 사실·메모", "textarea", 2000],
        ["checked_on", "확인일", "date", 10],
      ].forEach(function (item) {
        var label = document.createElement("label"),
          input = document.createElement(
            item[2] === "textarea" ? "textarea" : "input",
          );
        label.className = "field";
        var labelText = document.createElement("span");
        text(labelText, item[1]);
        input.className = "input sm";
        if (item[2] !== "textarea") input.type = item[2];
        else input.rows = 3;
        input.maxLength = item[3];
        input.value = source[item[0]] || "";
        input.addEventListener("input", function () {
          source[item[0]] = input.value;
          if (item[0] !== "checked_on") {
            source.verified = false;
            checkbox.checked = false;
          }
          serializeSources();
          changed(true);
        });
        label.append(labelText, input);
        row.append(label);
      });
      var checkedLabel = document.createElement("label"),
        checkbox = document.createElement("input");
      checkedLabel.className = "wr-source-verified";
      checkbox.type = "checkbox";
      checkbox.checked = source.verified === true;
      checkbox.addEventListener("change", function () {
        source.verified = checkbox.checked;
        serializeSources();
        changed(true);
      });
      checkedLabel.append(
        checkbox,
        document.createTextNode(" 직접 읽고 사실을 확인했습니다"),
      );
      row.append(checkedLabel);
      container.append(row);
    });
    document.getElementById("wr-source-empty").hidden = sources.length > 0;
    serializeSources();
  }
  function pane(name) {
    document.querySelectorAll("[data-section]").forEach(function (section) {
      section.hidden = section.dataset.section !== name;
    });
    document.querySelectorAll("[data-pane]").forEach(function (button) {
      var active = button.dataset.pane === name;
      button.classList.toggle("on", active);
      button.setAttribute("aria-current", active ? "step" : "false");
    });
    if (!busy && (name === "review" || name === "transfer"))
      refresh().catch(function () {});
    try {
      sessionStorage.setItem(storagePrefix + "-pane", name);
    } catch (_) {}
  }
  async function refresh() {
    try {
      var result = await request(root.dataset.preview, new FormData(form));
      render(result);
      bundle.html = result.html;
      bundle.plain = result.plain;
      bundle.prompt = result.prompt;
      bundle.markdown = result.markdown;
      return result;
    } catch (exc) {
      showError(exc.message);
      throw exc;
    }
  }
  var priorDisabled = [];
  function setBusy(value) {
    busy = value;
    if (value) {
      priorDisabled = Array.from(form.elements).map(function (input) {
        return [input, input.disabled];
      });
      priorDisabled.forEach(function (pair) {
        pair[0].disabled = true;
      });
      text(state, "원고 작업 중…");
    } else {
      priorDisabled.forEach(function (pair) {
        pair[0].disabled = pair[1];
      });
      priorDisabled = [];
    }
    root.classList.toggle("wr-busy", value);
  }
  async function perform(action, extra) {
    if (busy) return;
    try {
      await save(false);
      var data = new FormData();
      data.append("csrfmiddlewaretoken", field("csrfmiddlewaretoken").value);
      data.append("revision", field("revision").value);
      data.append("signature", field("signature").value);
      data.append("action", action);
      if (extra)
        Object.keys(extra).forEach(function (key) {
          data.append(key, extra[key]);
        });
      setBusy(true);
      var result = await request(root.dataset.action, data);
      setBusy(false);
      applyValues(result.values);
      field("revision").value = result.revision;
      field("signature").value = result.signature;
      bundle = result;
      savedFingerprint = fingerprint();
      dirty = false;
      clearOwnBackup();
      render(result);
      clearError();
      text(state, result.saved_at + " 저장됨");
      pane("write");
    } catch (exc) {
      setBusy(false);
      showError(exc.message);
      text(state, "원고 작업 확인 필요");
    }
  }
  function fallback(title, value) {
    text(document.getElementById("wr-dialog-title"), title);
    document.getElementById("wr-copy-fallback").value = value;
    document.getElementById("wr-copy-dialog").showModal();
  }
  async function copy(kind) {
    text(state, "복사 준비 중…");
    try {
      await save(false);
      var data = await refresh(),
        value = {
          title: field("title").value,
          tags: field("tags").value,
          html: data.html,
          prompt: data.prompt,
          rich: data.html,
        }[kind];
      if (
        kind === "rich" &&
        window.ClipboardItem &&
        navigator.clipboard &&
        navigator.clipboard.write
      ) {
        await navigator.clipboard.write([
          new ClipboardItem({
            "text/html": new Blob([data.html], { type: "text/html" }),
            "text/plain": new Blob([data.plain], { type: "text/plain" }),
          }),
        ]);
      } else if (
        kind !== "rich" &&
        navigator.clipboard &&
        navigator.clipboard.writeText
      ) {
        await navigator.clipboard.writeText(value);
      } else {
        fallback(
          kind === "rich"
            ? "서식 복사 미지원 · HTML모드에 붙여넣기"
            : "복사할 내용",
          value,
        );
        return;
      }
      text(state, "클립보드에 복사했습니다");
    } catch (exc) {
      if (!dirty) {
        var value = {
          title: field("title").value,
          tags: field("tags").value,
          html: bundle.html,
          prompt: bundle.prompt,
          rich: bundle.html,
        }[kind];
        fallback("직접 복사", value || "");
      } else {
        showError(exc.message);
        try {
          var current = await refresh();
          var unsaved = {
            title: field("title").value,
            tags: field("tags").value,
            html: current.html,
            rich: current.html,
            prompt: current.prompt,
          }[kind];
          fallback("저장 전 편집 내용 · 직접 복사", unsaved || body.value);
        } catch (_) {
          fallback("저장 전 원고 · 현재 Markdown 본문", body.value);
        }
      }
    }
  }
  function insert(kind) {
    var start = body.selectionStart,
      end = body.selectionEnd,
      selected = body.value.slice(start, end),
      add;
    var bits = {
      h2: "\n\n## " + (selected || "[[소제목]]") + "\n",
      h3: "\n\n### " + (selected || "[[작은 제목]]") + "\n",
      bold: "**" + (selected || "[[강조할 내용]]") + "**",
      list: "\n- " + (selected || "[[항목]]") + "\n",
      quote: "\n> " + (selected || "[[인용과 출처]]") + "\n",
      link: "[" + (selected || "[[링크 제목]]") + "](https://[[원문주소]])",
      table:
        "\n\n| 비교 기준 | 선택지 A | 선택지 B |\n|---|---|---|\n| [[기준]] | [[내용]] | [[내용]] |\n\n",
      image: "\n\n[[이미지: 용도·대체 텍스트·출처. 티스토리에서 업로드]]\n\n",
    };
    add = bits[kind];
    body.setRangeText(add, start, end, "end");
    body.focus();
    changed(true);
  }
  form.addEventListener("input", function (event) {
    if (!event.target.closest(".wr-source"))
      changed(
        [
          "body",
          "title",
          "question",
          "answer",
          "experience",
          "commercial",
          "profile",
          "template_key",
        ].includes(event.target.name),
      );
  });
  form.addEventListener("change", function (event) {
    if (!event.target.closest(".wr-source"))
      changed(
        ["profile", "template_key", "commercial"].includes(event.target.name),
      );
  });
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    save(false).catch(function () {});
  });
  document.addEventListener("keydown", function (event) {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      save(false).catch(function () {});
    }
  });
  document
    .querySelectorAll("[data-pane],[data-switch]")
    .forEach(function (button) {
      button.addEventListener("click", function () {
        pane(button.dataset.pane || button.dataset.switch);
      });
    });
  document.querySelectorAll("[data-wr-action]").forEach(function (button) {
    button.addEventListener("click", function () {
      perform(button.dataset.wrAction);
    });
  });
  document.querySelectorAll("[data-restore]").forEach(function (button) {
    button.addEventListener("click", function () {
      perform("restore", { version: button.dataset.restore });
    });
  });
  document.querySelectorAll("[data-copy-kind]").forEach(function (button) {
    button.addEventListener("click", function () {
      copy(button.dataset.copyKind);
    });
  });
  document.querySelectorAll("[data-insert]").forEach(function (button) {
    button.addEventListener("click", function () {
      insert(button.dataset.insert);
    });
  });
  document.querySelectorAll("[data-download]").forEach(function (link) {
    link.addEventListener("click", async function (event) {
      event.preventDefault();
      try {
        await save(false);
        window.location.href = link.href;
      } catch (_) {}
    });
  });
  document
    .getElementById("wr-add-source")
    .addEventListener("click", function () {
      if (sources.length >= 30) {
        showError("자료는 최대 30개까지 추가할 수 있습니다.");
        return;
      }
      sources.push({
        title: "",
        url: "",
        note: "",
        checked_on: "",
        verified: false,
      });
      renderSources();
      changed(true);
    });
  document
    .getElementById("wr-refresh-review")
    .addEventListener("click", function () {
      refresh().catch(function () {});
    });
  document
    .getElementById("wr-refresh-titles")
    .addEventListener("click", function () {
      refresh().catch(function () {});
    });
  document
    .getElementById("wr-dialog-close")
    .addEventListener("click", function () {
      document.getElementById("wr-copy-dialog").close();
    });
  document
    .getElementById("wr-dialog-select")
    .addEventListener("click", function () {
      document.getElementById("wr-copy-fallback").select();
    });
  document
    .getElementById("wr-reload-versions")
    .addEventListener("click", async function (event) {
      event.preventDefault();
      try {
        await save(false);
        window.location.reload();
      } catch (_) {}
    });
  document
    .getElementById("wr-duplicate")
    .addEventListener("click", async function () {
      try {
        await save(false);
        var data = new FormData();
        data.append("csrfmiddlewaretoken", field("csrfmiddlewaretoken").value);
        var response = await fetch(this.dataset.url, {
          method: "POST",
          body: data,
          credentials: "same-origin",
        });
        if (
          response.ok &&
          response.redirected &&
          new URL(response.url).pathname.startsWith("/blog/writing/")
        )
          window.location.href = response.url;
        else showError("원고를 복사하지 못했습니다.");
      } catch (exc) {
        showError(exc.message);
      }
    });
  document
    .getElementById("wr-local-download")
    .addEventListener("click", localBackupDownload);
  window.addEventListener("beforeunload", function (event) {
    if (dirty) {
      browserBackup();
      event.preventDefault();
      event.returnValue = "";
    }
  });
  renderSources();
  savedFingerprint = fingerprint();
  render(bundle);
  try {
    Object.keys(localStorage).forEach(function (key) {
      if (key !== storagePrefix && !key.startsWith(storagePrefix + "-")) return;
      var record;
      try {
        record = JSON.parse(localStorage.getItem(key));
      } catch (_) {
        return;
      }
      if (
        record &&
        record.values &&
        (!recovered || record.updated > recovered.updated)
      ) {
        recovered = record;
        recoveredKey = key;
      }
    });
  } catch (_) {}
  if (recovered && recovered.values) {
    document.getElementById("wr-recovery").hidden = false;
    if (recovered.signature !== bundle.signature)
      text(
        document.getElementById("wr-recovery").querySelector("span"),
        "브라우저의 편집 내용과 서버 원고가 다릅니다. 복구하면 브라우저 내용을 현재 원고로 사용합니다.",
      );
  }
  document.getElementById("wr-recover").addEventListener("click", function () {
    if (!recovered) return;
    var values = recovered.values;
    values.commercial = values.commercial === "on";
    applyValues(values);
    recoveryToClear.push(recoveredKey);
    document.getElementById("wr-recovery").hidden = true;
    changed(true);
    pane("write");
    save(false).catch(function () {});
  });
  document.getElementById("wr-discard").addEventListener("click", function () {
    try {
      localStorage.removeItem(recoveredKey);
    } catch (_) {}
    document.getElementById("wr-recovery").hidden = true;
  });
  var initialPane = body.value ? "write" : "brief";
  try {
    initialPane =
      sessionStorage.getItem(storagePrefix + "-pane") || initialPane;
  } catch (_) {}
  pane(
    ["brief", "write", "review", "transfer"].includes(initialPane)
      ? initialPane
      : "brief",
  );
})();
