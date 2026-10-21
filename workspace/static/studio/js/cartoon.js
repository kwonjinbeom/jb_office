/* 창작콘텐츠 › 인스타 카툰 화면 (2026-10-22). 마감·보기 바꾸기, 한 장씩 넘기기, PNG·ZIP 저장. */
(function () {
  "use strict";
  const D = window.Doodle, work = JSON.parse(document.getElementById("cc-work").textContent);
  const root = document.querySelector("[data-cc-cartoon]");
  if (!root) return;
  const $ = (s) => document.querySelector(s);
  const state = { finish: "paint", view: "one", i: 0 };
  try {
    const saved = JSON.parse(localStorage.getItem("cc.cartoon") || "{}");
    if (D.FINISHES[saved.finish]) state.finish = saved.finish;
    if (saved.view === "all") state.view = "all";
  } catch (e) {}
  const remember = () => { try { localStorage.setItem("cc.cartoon", JSON.stringify({ finish: state.finish, view: state.view })); } catch (e) {} };

  function slideSVG(i) { return D.slide(work, i, state.finish).toSVG("cc-svg"); }

  function render() {
    document.querySelectorAll("[data-cc-finish] button").forEach((b) => b.classList.toggle("on", b.dataset.v === state.finish));
    document.querySelectorAll("[data-cc-view] button").forEach((b) => b.classList.toggle("on", b.dataset.v === state.view));
    const one = $("[data-cc-one]"), all = $("[data-cc-all]");
    one.hidden = state.view !== "one"; all.hidden = state.view !== "all";
    $("[data-cc-png]").disabled = state.view !== "one";
    if (state.view === "one") {
      $("[data-cc-slide]").innerHTML = slideSVG(state.i);
      $("[data-cc-prev]").disabled = state.i === 0;
      $("[data-cc-next]").disabled = state.i === work.cuts.length - 1;
    } else {
      all.innerHTML = work.cuts.map((_, i) => `<button type="button" class="cc-thumb" data-i="${i}" aria-label="${i + 1}장 크게 보기">${slideSVG(i)}</button>`).join("");
    }
    document.querySelectorAll("[data-cc-list] button").forEach((b) => b.classList.toggle("on", +b.dataset.i === state.i));
    $("[data-cc-pos]").textContent = `${state.i + 1} / ${work.cuts.length}`;
  }

  function go(i) { state.i = Math.max(0, Math.min(work.cuts.length - 1, i)); state.view = "one"; remember(); render(); }

  async function toBlob(i) {
    const S = D.slide(work, i, state.finish);
    const canvas = document.createElement("canvas");
    canvas.width = S.w; canvas.height = S.h;
    await S.drawTo(canvas.getContext("2d"));
    return new Promise((res) => canvas.toBlob(res, "image/png"));
  }
  function download(blob, name) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
  const fileName = (i) => `${work.key}_${state.finish}_${String(i + 1).padStart(2, "0")}.png`;

  document.addEventListener("click", async (e) => {
    const t = e.target.closest("button");
    if (!t) return;
    if (t.closest("[data-cc-finish]")) { state.finish = t.dataset.v; remember(); render(); }
    else if (t.closest("[data-cc-view]")) { state.view = t.dataset.v; remember(); render(); }
    else if (t.matches("[data-cc-prev]")) go(state.i - 1);
    else if (t.matches("[data-cc-next]")) go(state.i + 1);
    else if (t.closest("[data-cc-list]") || t.matches(".cc-thumb")) go(+t.dataset.i);
    else if (t.matches("[data-cc-png]")) {
      t.disabled = true;
      try { download(await toBlob(state.i), fileName(state.i)); } finally { t.disabled = false; }
    } else if (t.matches("[data-cc-zip]")) {
      if (!window.JSZip) { window.App && App.toast("ZIP 도구를 못 불러왔습니다. 인터넷 연결을 확인하세요.", "err"); return; }
      t.disabled = true;
      const label = t.innerHTML;
      try {
        const zip = new JSZip();
        for (let i = 0; i < work.cuts.length; i++) {
          t.textContent = `만드는 중 ${i + 1}/${work.cuts.length}`;
          zip.file(fileName(i), await toBlob(i));
        }
        download(await zip.generateAsync({ type: "blob" }), `${work.key}_${state.finish}_카툰.zip`);
      } finally { t.innerHTML = label; t.disabled = false; }
    }
  });
  document.addEventListener("keydown", (e) => {
    if (state.view !== "one" || e.target.closest("input, textarea, select")) return;
    if (e.key === "ArrowLeft") go(state.i - 1);
    if (e.key === "ArrowRight") go(state.i + 1);
  });

  D.ready().then(render);
  render();
})();
