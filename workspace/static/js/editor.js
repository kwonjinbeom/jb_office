/* 티스토리 글쓰기 편집기 (writing/form.html).
   기본모드: 블로그 본문 모양 그대로 쓰는 contenteditable. HTML 모드: 같은 내용을 HTML 로 고친다.
   저장할 때 본문 HTML 을 숨은 body 칸에 옮겨 담고, 서버가 허용한 태그·속성만 남긴다 (apps/writing/render.py).
   붙여넣기: 마크다운·웹 문서·일반 글을 서버(convert)로 보내 블로그 서식 HTML 로 바꿔 넣는다. */
(function () {
  "use strict";
  var form = document.querySelector("form[data-editor-form]");
  var ed = document.getElementById("wr-editor");
  if (!form || !ed) return;

  var bar = document.querySelector("[data-editor-toolbar]");
  var src = document.getElementById("wr-html-src");
  var bodyField = form.querySelector("textarea[name=body]");
  var countEl = document.querySelector("[data-ed-count]");
  var blockSel = bar.querySelector("[data-ed-block]");
  var mode = "visual";
  var saved = null;  // 툴바를 누르기 전 커서 위치

  // 붙여넣기용 인라인 style (render.py 와 같은 값)
  var S = {
    photo: "margin:18px 0;padding:14px;border:1px dashed #fca5a5;border-radius:8px;background:#fef2f2;text-align:center;color:#374151;font-size:14px",
    figure: "margin:18px 0;padding:14px;border:1px dashed #93c5fd;border-radius:8px;background:#eff6ff;text-align:center;color:#374151;font-size:14px",
    caption: "text-align:center;color:#6b7280;font-size:14px;margin-top:-8px",
    table: "border-collapse:collapse;width:100%;font-size:15px",
    th: "border:1px solid #d1d5db;background:#f3f4f6;padding:8px;text-align:left",
    td: "border:1px solid #d1d5db;padding:8px;text-align:left",
    quote: "margin:18px 0;padding:12px 16px;border-left:4px solid #d1d5db;background:#f9fafb;color:#374151",
    hr: "border:0;border-top:1px solid #e5e7eb;margin:28px 0",
    img: "max-width:100%;height:auto"
  };

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function toast(msg, kind) { if (window.App && window.App.toast) window.App.toast(msg, kind); }

  try {
    document.execCommand("defaultParagraphSeparator", false, "p");
    document.execCommand("styleWithCSS", false, false);
  } catch (e) {}

  // ---- 커서
  function inEditor(node) { return node && (node === ed || ed.contains(node)); }
  function rememberRange() {
    var sel = window.getSelection();
    if (sel.rangeCount && inEditor(sel.anchorNode)) saved = sel.getRangeAt(0).cloneRange();
  }
  function restoreRange() {
    ed.focus();
    var sel = window.getSelection();
    if (saved) { sel.removeAllRanges(); sel.addRange(saved); return; }
    if (!sel.rangeCount || !inEditor(sel.anchorNode)) {  // 커서가 없으면 맨 끝에
      var r = document.createRange();
      r.selectNodeContents(ed);
      r.collapse(false);
      sel.removeAllRanges();
      sel.addRange(r);
    }
  }
  function currentBlock() {
    var sel = window.getSelection();
    var n = sel.rangeCount ? sel.anchorNode : null;
    while (n && n !== ed) {
      if (n.nodeType === 1 && n.parentNode === ed) return n;
      n = n.parentNode;
    }
    return null;
  }
  function closest(tagRe) {
    var sel = window.getSelection();
    var n = sel.rangeCount ? sel.anchorNode : null;
    while (n && n !== ed) {
      if (n.nodeType === 1 && tagRe.test(n.tagName)) return n;
      n = n.parentNode;
    }
    return null;
  }
  function insertHTML(html) {
    restoreRange();
    document.execCommand("insertHTML", false, html);
    changed();
  }
  // 문단 단위로 넣는 것(상자·표·구분선): 지금 문단 뒤에 넣고 그 다음에 빈 문단을 둔다.
  function insertBlock(html, focusSelector) {
    restoreRange();
    var block = currentBlock();
    var tmp = document.createElement("div");
    tmp.innerHTML = html + "<p><br></p>";
    var first = tmp.firstChild, last = tmp.lastChild;
    var frag = document.createDocumentFragment();
    while (tmp.firstChild) frag.appendChild(tmp.firstChild);
    var empty = block && block.tagName === "P" && !block.textContent.trim() && !block.querySelector("img");
    if (empty) { ed.replaceChild(frag, block); }
    else if (block) { block.parentNode.insertBefore(frag, block.nextSibling); }
    else { ed.appendChild(frag); }
    var target = (focusSelector && first.querySelector && (first.matches(focusSelector) ? first : first.querySelector(focusSelector))) || last;
    var r = document.createRange();
    r.selectNodeContents(target);
    if (target === last) r.collapse(true);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(r);
    saved = r.cloneRange();
    changed();
  }

  // ---- 툴바
  var actions = {
    photo: function () { insertBlock('<p class="wr-slot" style="' + S.photo + '">📷 여기에 올릴 사진 설명</p>', "p"); },
    figure: function () {
      var name = window.prompt("올릴 그림 파일 이름 (예: 그림1_시기표.png)", "");
      if (name === null) return;
      insertBlock('<p class="wr-slot" style="' + S.figure + '">🖼 여기에 그림 올리기: <strong>' + esc(name || "그림 파일") + "</strong></p>");
    },
    image: function () {
      var url = window.prompt("이미지 주소 (https://…)", "https://");
      if (!url || !/^https?:\/\/\S+$/.test(url)) return;
      insertBlock('<p style="text-align:center;margin:18px 0"><img src="' + esc(url) + '" alt="" style="' + S.img + '"></p>');
    },
    caption: function () { insertBlock('<p style="' + S.caption + '">캡션을 입력하세요</p>', "p"); },
    quote: function () {
      restoreRange();
      var bq = closest(/^BLOCKQUOTE$/);
      document.execCommand("formatBlock", false, bq ? "<p>" : "<blockquote>");
      changed();
    },
    // 머리글 줄도 보통 칸(td) + 굵게 + 회색 바탕: 티스토리 기본 모드는 <thead>/<th> 줄을 표 밖으로 빼 버린다.
    table: function () {
      var head = "<tr>" + [1, 2, 3].map(function () { return '<td style="' + S.th + '"><strong>항목</strong></td>'; }).join("") + "</tr>";
      var row = "<tr>" + [1, 2, 3].map(function () { return '<td style="' + S.td + '"><br></td>'; }).join("") + "</tr>";
      insertBlock('<table style="' + S.table + '"><tbody>' + head + row + row + "</tbody></table>", "strong");
    },
    addRow: function () {
      restoreRange();
      var tr = closest(/^TR$/), table = closest(/^TABLE$/);
      if (!tr || !table) return;
      var body = table.tBodies[0] || table;
      var n = tr.children.length, html = "";
      for (var i = 0; i < n; i++) html += '<td style="' + S.td + '"><br></td>';
      var nr = document.createElement("tr");
      nr.innerHTML = html;
      if (tr.parentNode === body) body.insertBefore(nr, tr.nextSibling); else body.insertBefore(nr, body.firstChild);
      changed();
    },
    addCol: function () {
      restoreRange();
      var table = closest(/^TABLE$/);
      if (!table) return;
      Array.prototype.forEach.call(table.rows, function (r, i) {
        var head = i === 0;  // 첫 줄이 머리글
        var c = document.createElement("td");
        c.setAttribute("style", head ? S.th : S.td);
        c.innerHTML = head ? "<strong>항목</strong>" : "<br>";
        r.appendChild(c);
      });
      changed();
    },
    link: function () {
      restoreRange();
      var url = window.prompt("링크 주소 (https://…)", "https://");
      if (!url || !/^(https?:\/\/|mailto:)\S+$/.test(url)) return;
      var sel = window.getSelection();
      if (sel.isCollapsed) document.execCommand("insertHTML", false, '<a href="' + esc(url) + '">' + esc(url) + "</a>");
      else document.execCommand("createLink", false, url);
      changed();
    },
    hr: function () { insertBlock('<hr style="' + S.hr + '">'); },
    markdown: function () { openMarkdown(); }
  };

  bar.addEventListener("mousedown", function (e) {
    // 툴바를 눌러도 본문 커서가 사라지지 않게 한다 (select 는 열려야 하니 제외)
    if (e.target.closest("button")) e.preventDefault();
  });
  bar.addEventListener("click", function (e) {
    var b = e.target.closest("[data-ed]");
    if (!b || b.disabled) return;
    if (mode !== "visual" && b.getAttribute("data-ed") !== "markdown") { toast("기본모드에서 쓸 수 있어요.", "info"); return; }
    var cmd = b.getAttribute("data-ed");
    if (actions[cmd]) { actions[cmd](); }
    else { restoreRange(); document.execCommand(cmd, false, null); changed(); }
    refreshState();
  });
  blockSel.addEventListener("change", function () {
    restoreRange();
    document.execCommand("formatBlock", false, "<" + blockSel.value + ">");
    changed();
    refreshState();
  });

  // 지금 커서 위치의 서식을 툴바에 켜 둔다
  function refreshState() {
    if (mode !== "visual") return;
    ["bold", "italic", "underline", "strikeThrough", "insertUnorderedList", "insertOrderedList", "justifyCenter"].forEach(function (c) {
      var b = bar.querySelector('[data-ed="' + c + '"]');
      var on = false;
      try { on = document.queryCommandState(c); } catch (e) {}
      if (b) b.classList.toggle("on", !!on);
    });
    var blk = currentBlock();
    var tag = blk ? blk.tagName.toLowerCase() : "p";
    blockSel.value = /^h[234]$/.test(tag) ? tag : "p";
    var inTable = !!closest(/^TABLE$/);
    bar.querySelector('[data-ed="addRow"]').disabled = !inTable;
    bar.querySelector('[data-ed="addCol"]').disabled = !inTable;
    bar.querySelector('[data-ed="quote"]').classList.toggle("on", !!closest(/^BLOCKQUOTE$/));
  }
  document.addEventListener("selectionchange", function () {
    var sel = window.getSelection();
    if (sel.rangeCount && inEditor(sel.anchorNode)) { rememberRange(); refreshState(); }
  });

  // ---- 붙여넣기: 서버에서 블로그 서식으로 바꿔 넣는다
  var MD_HINT = /^(#{1,4} |[-*] |\d+\. |> |\|.*\||\[(사진|그림|캡션)\]|📷|🖼|!\[|---\s*$)|\*\*[^*]+\*\*/m;
  function convert(kind, content) {
    var fd = new FormData();
    fd.append("kind", kind);
    fd.append("content", content);
    fd.append("csrfmiddlewaretoken", form.querySelector("[name=csrfmiddlewaretoken]").value);
    return fetch(form.getAttribute("data-convert-url"), { method: "POST", body: fd, credentials: "same-origin" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) { return d.html; });
  }
  ed.addEventListener("paste", function (e) {
    var cd = e.clipboardData;
    if (!cd) return;
    var text = cd.getData("text/plain"), html = cd.getData("text/html");
    e.preventDefault();
    rememberRange();
    var kind = MD_HINT.test(text) ? "markdown" : (html ? "html" : "text");
    convert(kind, kind === "html" ? html : text).then(
      function (out) { if (out) insertHTML(out); },
      function () { insertHTML(esc(text).replace(/\n/g, "<br>")); toast("서식을 바꾸지 못해 글자만 넣었어요.", "warn"); }
    );
  });

  // ---- 마크다운 넣기 창
  var dlg = document.getElementById("wr-md-dialog");
  function openMarkdown() {
    rememberRange();
    if (dlg && dlg.showModal) { dlg.querySelector("[data-md-input]").value = ""; dlg.showModal(); }
  }
  if (dlg) {
    dlg.addEventListener("close", function () {
      var how = dlg.returnValue, md = dlg.querySelector("[data-md-input]").value;
      if ((how !== "insert" && how !== "replace") || !md.trim()) return;
      if (mode !== "visual") setMode("visual");
      convert("markdown", md).then(function (out) {
        if (how === "replace") {
          if (ed.textContent.trim() && !window.confirm("지금 본문을 지우고 바꿀까요?")) return;
          ed.innerHTML = out; saved = null; changed();
        } else { insertHTML(out); }
        toast("마크다운을 서식으로 바꿔 넣었어요.", "ok");
      }, function () { toast("바꾸지 못했어요. 잠시 뒤 다시 해 주세요.", "error"); });
    });
  }

  // ---- 모드: 기본모드 ↔ HTML
  function setMode(m) {
    if (m === mode) return;
    if (m === "html") { src.value = ed.innerHTML; ed.hidden = true; src.hidden = false; autogrow(src); src.focus(); }
    else { ed.innerHTML = src.value; src.hidden = true; ed.hidden = false; saved = null; changed(); }
    mode = m;
    document.querySelectorAll("[data-ed-mode]").forEach(function (b) { b.classList.toggle("on", b.getAttribute("data-ed-mode") === m); });
    bar.classList.toggle("is-html", m === "html");
  }
  document.querySelectorAll("[data-ed-mode]").forEach(function (b) {
    b.addEventListener("click", function () { setMode(b.getAttribute("data-ed-mode")); });
  });
  function autogrow(t) { t.style.height = "auto"; t.style.height = Math.max(420, t.scrollHeight + 2) + "px"; }
  src.addEventListener("input", function () { autogrow(src); });

  // ---- 글자 수·빈 본문 안내
  function changed() {
    var clone = ed.cloneNode(true);
    Array.prototype.forEach.call(clone.querySelectorAll(".wr-slot"), function (n) { n.remove(); });
    var t = (clone.innerText || clone.textContent || "").replace(/\n{2,}/g, "\n").trim();
    if (countEl) countEl.textContent = "본문 " + t.length.toLocaleString() + "자 · 공백 제외 " + t.replace(/\s/g, "").length.toLocaleString() + "자";
    var empty = !ed.textContent.trim() && !ed.querySelector("img,table,hr,.wr-slot");
    ed.classList.toggle("is-empty", empty);
  }
  ed.addEventListener("input", changed);

  // 제목 칸에서 Enter 는 줄바꿈 대신 본문으로. 높이는 글 길이에 맞춘다 (화면이 다 그려진 뒤 다시 잰다).
  var title = form.querySelector("[name=title]");
  function sizeTitle() {
    if (!title) return;
    title.style.height = "auto";
    title.style.height = title.scrollHeight + "px";
  }
  if (title) {
    title.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); ed.focus(); }
    });
    title.addEventListener("input", sizeTitle);
    // 탭이 가려진 채 열리면 폭이 0 으로 재져 높이가 크게 나온다. 폭이 바뀔 때마다 다시 잰다.
    var lastW = 0;
    if (window.ResizeObserver) {
      new ResizeObserver(function (entries) {
        var w = Math.round(entries[0].contentRect.width);
        if (w && w !== lastW) { lastW = w; sizeTitle(); }
      }).observe(title);
    } else {
      window.addEventListener("resize", sizeTitle);
    }
    document.addEventListener("visibilitychange", function () { if (!document.hidden) sizeTitle(); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(sizeTitle);
  }

  // ---- 저장
  form.addEventListener("submit", function () {
    var html = mode === "html" ? src.value : ed.innerHTML;
    bodyField.value = html.replace(/^\s*(<p><br><\/p>\s*)+$/, "").trim();
  });
  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === "s" || e.key === "S")) {
      e.preventDefault();
      if (form.requestSubmit) form.requestSubmit(); else form.submit();
    }
  });

  if (!ed.innerHTML.trim()) ed.innerHTML = "<p><br></p>";
  changed();
})();
