/* 네이버 스마트에디터를 관찰해 만든 별도 편집기 (naver_writing/form.html).
   네이버의 문서형 화면에서 본문을 직접 편집한다.
   저장할 때 본문 HTML 을 숨은 body 칸에 옮겨 담고, 서버가 허용한 태그·속성만 남긴다 (apps/naver_writing/render.py).
   붙여넣기: 마크다운·웹 문서·일반 글을 서버(convert)로 보내 블로그 서식 HTML 로 바꿔 넣는다. */
(function () {
  "use strict";
  var form = document.querySelector("form[data-editor-form]");
  var ed = document.getElementById("wr-editor");
  if (!form || !ed) return;

  var bar = document.querySelector("[data-editor-toolbar]");
  var bodyField = form.querySelector("textarea[name=body]");
  var countEl = document.querySelector("[data-ed-count]");
  var blockSel = bar.querySelector('[data-nv-select="block"]');
  var config = JSON.parse(document.getElementById("nv-editor-config").textContent);
  var ready = false, history = [], historyIndex = -1, replaying = false, pending = 0;
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
    document.execCommand("styleWithCSS", false, true);
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
    if (saved && inEditor(saved.commonAncestorContainer)) { sel.removeAllRanges(); sel.addRange(saved); return; }
    saved = null;
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
  };

  function selectedBlocks() {
    var sel = window.getSelection();
    if (!sel.rangeCount || !inEditor(sel.anchorNode)) return [];
    var range = sel.getRangeAt(0);
    var blocks = Array.from(ed.querySelectorAll("p,h2,h3,h4,li,td,blockquote,pre"))
      .filter(function (node) { return range.intersectsNode(node) && !node.querySelector("p,h2,h3,h4,li,td,blockquote,pre"); });
    return blocks.length ? blocks : [currentBlock()].filter(Boolean);
  }
  function applyStyle(name, value) {
    restoreRange();
    if (["text-align", "line-height"].indexOf(name) >= 0) {
      selectedBlocks().forEach(function (node) { node.style.setProperty(name, value); });
    } else {
      var command = {"font-family":"fontName", "color":"foreColor", "background-color":"hiliteColor"}[name];
      if (command) document.execCommand(command, false, value);
      else if (name === "font-size") {
        document.execCommand("fontSize", false, "7");
        ed.querySelectorAll('[style],font[size="7"]').forEach(function (node) {
          if (node.style.fontSize !== "xxx-large" && node.getAttribute("size") !== "7") return;
          if (node.tagName !== "FONT") { node.style.fontSize = value; return; }
          var span = document.createElement("span"); span.style.cssText=node.style.cssText;
          span.style.fontSize=value;
          while (node.firstChild) span.appendChild(node.firstChild);
          node.replaceWith(span);
        });
      }
    }
    rememberRange(); changed(); refreshState();
  }
  function undo(delta) {
    var target = historyIndex + delta;
    if (target < 0 || target >= history.length) return;
    replaying = true; historyIndex = target; ed.innerHTML = history[target]; saved = null;
    restoreRange(); changed(); refreshState(); replaying = false;
  }
  function refreshState() {
    ["bold","italic","underline","strikeThrough","superscript","subscript","insertUnorderedList","insertOrderedList"].forEach(function (cmd) {
      var button = bar.querySelector('[data-nv="' + cmd + '"]');
      var on = false; try { on = document.queryCommandState(cmd); } catch (err) {}
      if (button) { button.classList.toggle("on", on); button.setAttribute("aria-pressed", String(on)); }
    });
    var block = closest(/^(P|H2|H3|H4|BLOCKQUOTE|LI|TD)$/);
    var tag = block ? block.tagName.toLowerCase() : "p";
    blockSel.value = /^h[234]$/.test(tag) ? "h2" : tag === "blockquote" ? tag : "p";
    var node = window.getSelection().anchorNode;
    node = node && node.nodeType === 1 ? node : node && node.parentElement;
    if (node && inEditor(node)) {
      var css = getComputedStyle(node);
      [["font",css.fontFamily.split(",")[0].replace(/["']/g, "")],["size",String(parseFloat(css.fontSize))],
       ["align",css.textAlign],["line",String(Math.round(parseFloat(css.lineHeight)/parseFloat(css.fontSize)*100))]].forEach(function (pair) {
        var select = bar.querySelector('[data-nv-select="' + pair[0] + '"]');
        if (Array.from(select.options).some(function (o) { return o.value === pair[1]; })) select.value = pair[1];
      });
    }
    bar.querySelector(".nv-table-tools").hidden = !closest(/^TABLE$/);
    bar.querySelector('[data-nv="undo"]').disabled = historyIndex <= 0;
    bar.querySelector('[data-nv="redo"]').disabled = historyIndex >= history.length-1;
  }
  var insertDialog = document.getElementById("nv-insert-dialog");
  var insertForm = document.getElementById("nv-insert-form");
  var dialogKind = "";
  function openInsert(kind) {
    rememberRange(); dialogKind = kind; insertForm.reset();
    var titles = {image:"이미지 주소",figure:"그림 자리",link:"링크",caption:"캡션",table:"표 만들기",code:"소스코드",symbols:"특수문자"};
    insertForm.querySelector("#nv-dialog-title").textContent = titles[kind];
    insertForm.querySelector("[data-nv-dialog-help]").textContent = kind === "image" ? "웹 이미지 주소를 입력하세요. 내 컴퓨터의 사진은 사진 버튼으로 넣을 수 있어요." : kind === "figure" ? "나중에 올릴 그림의 파일 이름이나 설명을 적으세요." : "";
    insertForm.querySelector("[data-nv-label-wrap]").hidden = ["image","figure","link","caption"].indexOf(kind) < 0;
    insertForm.querySelector("[data-nv-url-wrap]").hidden = ["image","link"].indexOf(kind) < 0;
    insertForm.querySelector("[data-nv-text-wrap]").hidden = kind !== "code";
    insertForm.querySelector("[data-nv-table-wrap]").hidden = kind !== "table";
    insertForm.querySelector("[data-nv-symbols]").hidden = kind !== "symbols";
    insertForm.querySelector("[data-nv-dialog-insert]").hidden = kind === "symbols";
    insertForm.querySelector("[data-nv-dialog-error]").textContent = "";
    insertForm.querySelector("[data-nv-label-input]").value = kind === "link" ? window.getSelection().toString() : "";
    insertDialog.showModal();
  }
  insertForm.addEventListener("submit", function (e) {
    if (!e.submitter || e.submitter.value !== "insert") return;
    var label = insertForm.querySelector("[data-nv-label-input]").value.trim();
    var url = insertForm.querySelector("[data-nv-url]").value.trim();
    var error = insertForm.querySelector("[data-nv-dialog-error]");
    if (["image","link"].indexOf(dialogKind) >= 0 && !/^https?:\/\/[^\s]+$/i.test(url)) {
      e.preventDefault(); error.textContent = "http:// 또는 https://로 시작하는 주소를 입력하세요."; return;
    }
    if (dialogKind === "image") insertBlock('<p style="text-align:center;margin:18px 0"><img src="'+esc(url)+'" alt="'+esc(label)+'" style="'+S.img+'"></p>');
    if (dialogKind === "figure") insertBlock('<p class="wr-slot" style="'+S.figure+'">🖼 여기에 그림 올리기: <strong>'+esc(label || "그림 파일")+'</strong></p>');
    if (dialogKind === "link") insertHTML('<a href="'+esc(url)+'" target="_blank" rel="noopener">'+esc(label || url)+'</a>');
    if (dialogKind === "caption") insertBlock('<p style="'+S.caption+'">'+esc(label || "캡션")+'</p>');
    if (dialogKind === "code") insertBlock('<pre><code>'+esc(insertForm.querySelector("[data-nv-text]").value)+'</code></pre>');
    if (dialogKind === "table") {
      var rows = Number(insertForm.querySelector("[data-nv-rows]").value), cols = Number(insertForm.querySelector("[data-nv-cols]").value);
      if (!Number.isInteger(rows) || rows<1 || rows>30 || !Number.isInteger(cols) || cols<1 || cols>10) { e.preventDefault(); error.textContent="행은 1~30, 열은 1~10으로 입력하세요."; return; }
      var html = '<table style="'+S.table+'"><tbody>';
      for (var r=0;r<rows;r++) { html+="<tr>"; for (var c=0;c<cols;c++) html+='<td style="'+(r===0?S.th:S.td)+'">'+(r===0?"<strong>항목</strong>":"<br>")+'</td>'; html+='</tr>'; }
      insertBlock(html+'</tbody></table>',"td");
    }
    refreshState();
  });
  insertForm.querySelectorAll("[data-nv-symbol]").forEach(function (b) {
    b.addEventListener("click", function () { insertDialog.close(); insertHTML(esc(b.dataset.nvSymbol)); refreshState(); });
  });
  var preview = document.getElementById("nv-preview");
  var submitButtons = Array.from(document.querySelectorAll('button[type="submit"][form="post-form"]'));
  function busy(delta) { pending+=delta; submitButtons.forEach(function (b) { b.disabled=pending>0; }); }
  async function showPreview() {
    busy(1);
    try {
      var html = await convert("html",ed.innerHTML);
      preview.querySelector("[data-nv-preview-title]").textContent=title.value || "제목";
      preview.querySelector("[data-nv-preview-body]").innerHTML=html;
      var tags=preview.querySelector("[data-nv-preview-tags]"); tags.replaceChildren();
      form.querySelector("[name=tags]").value.split(/[,\n]/).forEach(function (t) { if (t.trim()) { var span=document.createElement("span"); span.textContent="#"+t.trim().replace(/^#+/,""); tags.appendChild(span); } });
      preview.showModal();
    } catch (err) { toast("미리보기를 불러오지 못했습니다. 다시 시도하세요.","error"); } finally { busy(-1); }
  }
  preview.querySelector("[data-nv-preview-close]").addEventListener("click",function () { preview.close(); });
  preview.querySelectorAll("[data-nv-preview-width]").forEach(function (b) { b.addEventListener("click", function () {
    preview.querySelector(".nv-preview-paper").classList.toggle("mobile",b.dataset.nvPreviewWidth==="mobile");
    preview.querySelectorAll("[data-nv-preview-width]").forEach(function (other) { other.classList.toggle("on",other===b); });
  }); });
  document.querySelectorAll("[data-nv-width]").forEach(function (b) { b.addEventListener("click",function () {
    document.getElementById("nv-editor-paper").classList.toggle("mobile", b.dataset.nvWidth==="mobile");
    document.querySelectorAll("[data-nv-width]").forEach(function (other) { other.classList.toggle("on",other===b); }); sizeTitle();
  }); });
  async function insertPhotos(files) {
    rememberRange(); busy(1);
    try {
      for (var file of files) {
        if (!["image/jpeg","image/png","image/webp"].includes(file.type) || file.size>10*1024*1024) { toast("JPG·PNG·WEBP 사진을 골라주세요. 한 장에 최대 10MB입니다.","warn"); continue; }
        var bitmap=await createImageBitmap(file), scale=Math.min(1,1600/Math.max(bitmap.width,bitmap.height));
        var canvas=document.createElement("canvas"); canvas.width=Math.max(1,Math.round(bitmap.width*scale)); canvas.height=Math.max(1,Math.round(bitmap.height*scale));
        var ctx=canvas.getContext("2d"); ctx.fillStyle="#ffffff"; ctx.fillRect(0,0,canvas.width,canvas.height); ctx.drawImage(bitmap,0,0,canvas.width,canvas.height); bitmap.close();
        var data=canvas.toDataURL("image/jpeg",0.85);
        if(data.length>1400000 || new Blob([ed.innerHTML]).size+data.length>1900000) { toast("본문 사진 용량이 큽니다. 사진 수를 줄이거나 이미지 주소를 사용하세요.","warn"); continue; }
        insertBlock('<p style="text-align:center;margin:18px 0"><img src="'+data+'" alt="'+esc(file.name)+'" style="'+S.img+'"></p>');
      }
    } catch (err) { toast("사진을 읽지 못했습니다.","error"); } finally { busy(-1); }
  }
  var photoInput=document.getElementById("nv-photo-input");
  photoInput.addEventListener("change",function () { insertPhotos(Array.from(photoInput.files)); photoInput.value=""; });
  bar.addEventListener("mousedown",function (e) { if(e.target.closest("button,summary")) e.preventDefault(); });
  bar.addEventListener("click",function (e) {
    var b=e.target.closest("[data-nv]"); if(!b || b.disabled) return;
    var cmd=b.dataset.nv;
    if(["image","figure","link","caption","table","code","symbols"].includes(cmd)) openInsert(cmd);
    else if(cmd==="photos") { rememberRange(); photoInput.click(); }
    else if(cmd==="photo-slot") actions.photo();
    else if(cmd==="markdown") openMarkdown();
    else if(cmd==="preview") showPreview();
    else if(cmd==="undo" || cmd==="redo") undo(cmd==="undo"?-1:1);
    else if(cmd==="quote") insertBlock('<blockquote style="'+config.quotes[Number(b.dataset.value)]+'"><p>인용구를 입력하세요.</p></blockquote>',"p");
    else if(cmd==="divider") insertBlock('<hr style="'+config.dividers[Number(b.dataset.value)]+'">');
    else if(cmd==="row") actions.addRow();
    else if(cmd==="col") actions.addCol();
    else if(cmd==="removeRow" || cmd==="removeCol") {
      restoreRange(); var table=closest(/^TABLE$/), cell=closest(/^(TD|TH)$/), row=closest(/^TR$/);
      if(table && row && cell) {
        if(cmd==="removeRow") row.remove();
        else { var index=cell.cellIndex; Array.from(table.rows).forEach(function (r) { if(r.cells[index]) r.cells[index].remove(); }); }
        if(!table.rows.length || !table.rows[0].cells.length) table.remove();
        saved=null; changed();
      }
    } else { restoreRange(); document.execCommand(cmd,false,null); rememberRange(); changed(); }
    bar.querySelectorAll("details[open]").forEach(function (d) { d.open=false; }); refreshState();
  });
  bar.querySelectorAll("[data-nv-select]").forEach(function (select) {
    select.addEventListener("change",function () {
      var kind=select.dataset.nvSelect;
      if(kind==="block") { restoreRange(); document.execCommand("formatBlock",false,"<"+select.value+">"); changed(); }
      else applyStyle({font:"font-family",size:"font-size",align:"text-align",line:"line-height"}[kind],select.value+(kind==="size"?"px":kind==="line"?"%":""));
      refreshState();
    });
  });
  bar.querySelectorAll("[data-nv-color]").forEach(function (input) {
    input.addEventListener("input",function () { applyStyle(input.dataset.nvColor,input.value); });
  });
  bar.querySelectorAll("details.nv-picker").forEach(function (picker) {
    picker.addEventListener("toggle", function () {
      if (!picker.open) return;
      bar.querySelectorAll("details.nv-picker").forEach(function (other) { if (other !== picker) other.open=false; });
      var box=picker.querySelector("summary").getBoundingClientRect(), pop=picker.querySelector(".nv-popover");
      pop.style.left=Math.max(8,Math.min(window.innerWidth-195,box.left))+"px";
      pop.style.top=Math.min(box.bottom+2,window.innerHeight-180)+"px";
    });
  });
  document.addEventListener("click",function (e) {
    bar.querySelectorAll("details[open]").forEach(function (picker) { if(!picker.contains(e.target)) picker.open=false; });
  });
  document.addEventListener("keydown",function (e) {
    if(e.key==="Escape") bar.querySelectorAll("details[open]").forEach(function (picker) { picker.open=false; });
  });
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
    var pasteRange=saved && saved.cloneRange();
    var kind = MD_HINT.test(text) ? "markdown" : (html ? "html" : "text");
    if (cd.files && cd.files.length) { insertPhotos(Array.from(cd.files)); return; }
    busy(1);
    convert(kind, kind === "html" ? html : text).then(
      function (out) { if (out) { saved=pasteRange; insertHTML(out); } },
      function () { insertHTML(esc(text).replace(/\n/g, "<br>")); toast("서식을 바꾸지 못해 글자만 넣었어요.", "warn"); }
    ).finally(function () { busy(-1); });
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

      busy(1);
      convert("markdown", md).then(function (out) {
        if (how === "replace") {
          if (ed.textContent.trim() && !window.confirm("지금 본문을 지우고 바꿀까요?")) return;
          ed.innerHTML = out; saved = null; changed();
        } else { insertHTML(out); }
        toast("마크다운을 서식으로 바꿔 넣었어요.", "ok");
      }, function () { toast("바꾸지 못했어요. 잠시 뒤 다시 해 주세요.", "error"); }).finally(function () { busy(-1); });
    });
  }

  // ---- 글자 수·빈 본문 안내
  function changed() {
    var clone = ed.cloneNode(true);
    Array.prototype.forEach.call(clone.querySelectorAll(".wr-slot"), function (n) { n.remove(); });
    clone.querySelectorAll("br").forEach(function(n) { n.replaceWith(document.createTextNode("\n")); });
    clone.querySelectorAll("td,th").forEach(function(n) { if(n.nextElementSibling) n.appendChild(document.createTextNode("\t")); });
    clone.querySelectorAll("p,h2,h3,h4,li,tr,blockquote").forEach(function(n) { n.appendChild(document.createTextNode("\n")); });
    var t = clone.textContent.replace(/\n{3,}/g, "\n\n").trim();
    if (!replaying && history[historyIndex] !== ed.innerHTML) {
      history=history.slice(0,historyIndex+1); history.push(ed.innerHTML);
      if(history.length>40) history.shift(); historyIndex=history.length-1;
    }
    if(ready) { form.dispatchEvent(new Event("input",{bubbles:true})); document.querySelector("[data-nv-save-state]").textContent="저장하지 않은 변경"; }
    if (countEl) countEl.textContent = "본문 " + t.length.toLocaleString() + "자 · 공백 제외 " + t.replace(/\s/g, "").length.toLocaleString() + "자";
    var empty = !ed.textContent.trim() && !ed.querySelector("img,table,hr,.wr-slot");
    ed.classList.toggle("is-empty", empty);
    refreshState();
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
  form.addEventListener("submit", function (e) {
    if(pending) { e.preventDefault(); toast("본문을 준비하고 있습니다. 잠시 뒤 저장하세요.","info"); return; }
    var html = ed.innerHTML;
    bodyField.value = html.replace(/^\s*(<p><br><\/p>\s*)+$/, "").trim();
  });
  form.addEventListener("input", function () {
    if(ready) document.querySelector("[data-nv-save-state]").textContent="저장하지 않은 변경";
  });
  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === "s" || e.key === "S")) {
      if(document.querySelector("dialog[open]")) { e.preventDefault(); return; }
      if(pending) { e.preventDefault(); return; }
      e.preventDefault();
      if (form.requestSubmit) form.requestSubmit(); else form.submit();
    }
  });

  ed.addEventListener("keydown",function (e) {
    if((e.ctrlKey || e.metaKey) && ["z","y"].includes(e.key.toLowerCase()) && !e.isComposing) { e.preventDefault(); undo(e.key.toLowerCase()==="y" || e.shiftKey?1:-1); }
  });
  if (!ed.innerHTML.trim()) ed.innerHTML = "<p><br></p>";
  changed(); ready=true;
})();
