/* 모든 글 본문(.contents_style)에 jb-post 를 달아 글모양.css 를 건다 (2026-10-22 사용자: JB Office 변환 화면과 같은 모양).
   붙여넣을 때 끼운 빈 줄(빈 문단)이 하나도 없는 예전 글은 jb-airy 를 더 달아 문단 아래를 빈 줄만큼 띄운다. */
(function () {
  function blank(p) {
    return !p.querySelector("img, iframe, video, figure, input, select") && !p.textContent.replace(/ /g, "").trim();
  }
  function mark() {
    var bodies = document.querySelectorAll("div.contents_style");
    for (var i = 0; i < bodies.length; i++) {
      var b = bodies[i];
      b.classList.add("jb-post");
      if (![].some.call(b.querySelectorAll("p"), blank)) b.classList.add("jb-airy");
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mark);
  else mark();
})();
