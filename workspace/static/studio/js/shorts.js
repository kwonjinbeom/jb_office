/* 창작콘텐츠 › 숏폼 영상 화면 (2026-10-22).
 * - 재생: 오디오 시계에 맞춰 장면을 그린다 (초당 30번). 효과음·배경음은 CCSound 가 그때그때 합성.
 * - 녹음: 처음부터 재생하며 마이크로 내 목소리를 받는다 (스피커 소리가 섞이지 않게 효과음은 끈다). 저장은 이 창 안에서만.
 * - MP4: WebCodecs 로 한 장면씩 그려 H.264 로 굽고, 소리는 OfflineAudioContext 로 만들어 AAC(안 되면 Opus)로 붙인다.
 */
(function () {
  "use strict";
  const D = window.Doodle, Snd = window.CCSound;
  const work = JSON.parse(document.getElementById("cc-work").textContent);
  const root = document.querySelector("[data-cc-shorts]");
  if (!root) return;
  const $ = (s) => document.querySelector(s);
  const tl = D.timeline(work), plan = Snd.plan(work), FPS = 30;
  const st = { finish: "paint", t: 0, playing: false, ctx: null, bus: null, base: 0, from: 0, raf: 0, lastDraw: -1,
    voice: null, voiceBuf: null, recording: false, busy: false };
  try { const f = localStorage.getItem("cc.shorts.finish"); if (D.FINISHES[f]) st.finish = f; } catch (e) {}

  const screen = $("[data-cc-screen]"), seek = $("[data-cc-seek]"), timeEl = $("[data-cc-time]");
  const toast = (m, k) => window.App && App.toast(m, k || "ok");

  function draw(t) {
    const { S, seg } = D.short(work, t, st.finish);
    screen.innerHTML = S.toSVG("cc-svg");
    seek.value = t.toFixed(2);
    timeEl.textContent = `${t.toFixed(1)} / ${tl.total.toFixed(1)}`;
    document.querySelectorAll("[data-cc-row]").forEach((r) => r.classList.toggle("on", +r.dataset.ccRow === seg.i));
    $("[data-cc-prompter]").innerHTML = `<span class="cc-k">${seg.i + 1}컷 녹음 대사</span>${App.esc(work.cuts[seg.i].narr)}`;
  }

  function audioCtx() {
    if (!st.ctx) st.ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 48000 });
    return st.ctx;
  }

  function play(from) {
    stop(true);
    const ctx = audioCtx();
    ctx.resume();
    st.from = from >= tl.total - .05 ? 0 : from;
    st.base = ctx.currentTime + .06;
    st.bus = ctx.createGain(); st.bus.connect(ctx.destination);
    const fx = $("[data-cc-fx]").checked && !st.recording, bgm = $("[data-cc-bgm]").checked && !st.recording;
    Snd.schedule(ctx, st.bus, plan, st.from, st.base, { fx, bgm });
    if (st.voiceBuf && $("[data-cc-voice]").checked && !st.recording) {
      const src = ctx.createBufferSource(); src.buffer = st.voiceBuf; src.connect(st.bus);
      src.start(st.base, st.from);
    }
    st.playing = true;
    setPlayIcon();
    const tick = () => {
      if (!st.playing) return;
      const t = Math.min(tl.total, st.from + Math.max(0, ctx.currentTime - st.base));
      const frame = Math.floor(t * FPS);
      if (frame !== st.lastDraw) { st.lastDraw = frame; st.t = t; draw(t); }
      if (t >= tl.total) { stop(); if (st.recording) finishRecording(); return; }
      st.raf = requestAnimationFrame(tick);
    };
    st.raf = requestAnimationFrame(tick);
  }

  function stop(keep) {
    cancelAnimationFrame(st.raf);
    if (st.bus) { try { st.bus.disconnect(); } catch (e) {} st.bus = null; }
    st.playing = false;
    if (!keep) setPlayIcon();
  }
  function setPlayIcon() {
    const b = $("[data-cc-play]");
    b.innerHTML = `<svg class="ic"><use href="#i-${st.playing ? "pause" : "play"}"></use></svg>`;
    b.setAttribute("aria-label", st.playing ? "멈춤" : "재생");
  }

  // ---------- 내 목소리 녹음 ----------
  async function startRecording() {
    let stream;
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } }); }
    catch (e) { toast("마이크를 쓸 수 없습니다. 브라우저에서 마이크를 허용하세요.", "err"); return; }
    const chunks = [];
    const rec = new MediaRecorder(stream);
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
      try {
        st.voiceBuf = await audioCtx().decodeAudioData(await blob.arrayBuffer());
        st.voice = blob;
        const v = $("[data-cc-voice]"); v.disabled = false; v.checked = true;
        toast(`녹음했습니다 (${st.voiceBuf.duration.toFixed(1)}초). 재생하면 함께 나옵니다.`);
      } catch (e) { toast("녹음을 읽지 못했습니다.", "err"); }
    };
    st.recorder = rec;
    st.recording = true;
    setRecLabel();
    rec.start();
    play(0);
  }
  function finishRecording() {
    st.recording = false;
    setRecLabel();
    if (st.recorder && st.recorder.state !== "inactive") st.recorder.stop();
  }
  function setRecLabel() {
    const b = $("[data-cc-rec]");
    b.classList.toggle("danger", st.recording);
    b.querySelector("span").textContent = st.recording ? "녹음 멈추기" : (st.voiceBuf ? "다시 녹음" : "내 목소리 녹음");
  }

  // ---------- MP4 ----------
  async function pickVideo(W, H) {
    for (const codec of ["avc1.640028", "avc1.4d0028", "avc1.42e028"]) {
      const cfg = { codec, width: W, height: H, bitrate: 6_000_000, framerate: FPS };
      try { if ((await VideoEncoder.isConfigSupported(cfg)).supported) return cfg; } catch (e) {}
    }
    return null;
  }
  async function pickAudio() {
    for (const [codec, mux] of [["mp4a.40.2", "aac"], ["opus", "opus"]]) {
      const cfg = { codec, sampleRate: 48000, numberOfChannels: 2, bitrate: 128000 };
      try { if ((await AudioEncoder.isConfigSupported(cfg)).supported) return { cfg, mux }; } catch (e) {}
    }
    return null;
  }

  async function renderAudio(opts) {
    const len = Math.ceil(tl.total * 48000);
    const oac = new OfflineAudioContext(2, len, 48000);
    const bus = oac.createGain(); bus.connect(oac.destination);
    Snd.schedule(oac, bus, plan, 0, 0, opts);
    if (opts.voice && st.voiceBuf) { const s = oac.createBufferSource(); s.buffer = st.voiceBuf; s.connect(bus); s.start(0); }
    return oac.startRendering();
  }

  async function exportMp4(progress) {
    if (!("VideoEncoder" in window) || !window.Mp4Muxer) throw new Error("이 브라우저는 영상 굽기를 지원하지 않습니다 (크롬·엣지 최신판 필요).");
    const W = 1080, H = 1920, frames = Math.ceil(tl.total * FPS);
    const vcfg = await pickVideo(W, H), acfg = await pickAudio();
    if (!vcfg) throw new Error("H.264 인코더를 찾지 못했습니다.");
    const muxer = new Mp4Muxer.Muxer({
      target: new Mp4Muxer.ArrayBufferTarget(),
      video: { codec: "avc", width: W, height: H, frameRate: FPS },
      audio: acfg ? { codec: acfg.mux, numberOfChannels: 2, sampleRate: 48000 } : undefined,
      fastStart: "in-memory",
    });
    let failed = null;
    const venc = new VideoEncoder({ output: (c, m) => muxer.addVideoChunk(c, m), error: (e) => { failed = e; } });
    venc.configure(vcfg);
    const canvas = document.createElement("canvas"); canvas.width = W; canvas.height = H;
    const g = canvas.getContext("2d");
    for (let f = 0; f < frames; f++) {
      if (failed) throw failed;
      const { S } = D.short(work, f / FPS, st.finish);
      await S.drawTo(g);
      const vf = new VideoFrame(canvas, { timestamp: Math.round(f * 1e6 / FPS), duration: Math.round(1e6 / FPS) });
      venc.encode(vf, { keyFrame: f % (FPS * 2) === 0 });
      vf.close();
      while (venc.encodeQueueSize > 6) await new Promise((r) => setTimeout(r, 4));
      if (f % 6 === 0) progress(f / frames * .9);
    }
    await venc.flush();
    if (acfg) {
      progress(.92);
      const buf = await renderAudio({ fx: $("[data-cc-fx]").checked, bgm: $("[data-cc-bgm]").checked, voice: $("[data-cc-voice]").checked });
      const aenc = new AudioEncoder({ output: (c, m) => muxer.addAudioChunk(c, m), error: (e) => { failed = e; } });
      aenc.configure(acfg.cfg);
      const L = buf.getChannelData(0), R = buf.getChannelData(1), N = 4800;
      for (let i = 0; i < buf.length; i += N) {
        const n = Math.min(N, buf.length - i), data = new Float32Array(n * 2);
        data.set(L.subarray(i, i + n), 0); data.set(R.subarray(i, i + n), n);
        const ad = new AudioData({ format: "f32-planar", sampleRate: 48000, numberOfFrames: n, numberOfChannels: 2, timestamp: Math.round(i / 48000 * 1e6), data });
        aenc.encode(ad); ad.close();
      }
      await aenc.flush();
      if (failed) throw failed;
    }
    muxer.finalize();
    progress(1);
    return new Blob([muxer.target.buffer], { type: "video/mp4" });
  }

  // ---------- 이벤트 ----------
  function setFinish(f) {
    st.finish = f;
    try { localStorage.setItem("cc.shorts.finish", f); } catch (e) {}
    document.querySelectorAll("[data-cc-finish] button").forEach((b) => b.classList.toggle("on", b.dataset.v === f));
    st.lastDraw = -1; draw(st.t);
  }

  document.addEventListener("click", async (e) => {
    const b = e.target.closest("button");
    const row = e.target.closest("[data-cc-row]");
    if (row && !st.busy) { st.t = +row.dataset.start + .001; st.playing ? play(st.t) : draw(st.t); return; }
    if (!b) return;
    if (b.closest("[data-cc-finish]")) setFinish(b.dataset.v);
    else if (b.matches("[data-cc-play]")) { if (st.recording) return; st.playing ? (st.t = +seek.value, stop()) : play(st.t >= tl.total - .05 ? 0 : st.t); }
    else if (b.matches("[data-cc-rec]")) { if (st.busy) return; st.recording ? (stop(), finishRecording()) : startRecording(); }
    else if (b.matches("[data-cc-export]")) {
      if (st.busy) return;
      stop(); st.busy = true; b.disabled = true;
      const label = b.querySelector("span"), out = $("[data-cc-out]"), t0 = performance.now();
      try {
        const blob = await exportMp4((k) => { label.textContent = `굽는 중 ${Math.round(k * 100)}%`; });
        const url = URL.createObjectURL(blob), name = `${work.key}_${st.finish}_숏폼.mp4`;
        const sec = ((performance.now() - t0) / 1000).toFixed(0);
        out.hidden = false;
        out.innerHTML = `<div class="cc-out-head"><b>MP4 완성</b><span class="muted">${(blob.size / 1048576).toFixed(1)}MB · ${sec}초 걸림</span>` +
          `<a class="btn sm primary" href="${url}" download="${name}"><svg class="ic"><use href="#i-download"></use></svg>저장</a></div>` +
          `<video src="${url}" controls playsinline></video>`;
        window.__ccLastMp4 = { size: blob.size, ms: performance.now() - t0 };
      } catch (err) {
        toast(err.message || String(err), "err");
        window.__ccLastMp4 = { error: String(err) };
      } finally { label.textContent = "MP4 만들기"; b.disabled = false; st.busy = false; }
    }
  });
  seek.addEventListener("input", () => { st.t = +seek.value; st.playing ? play(st.t) : draw(st.t); });
  document.addEventListener("keydown", (e) => {
    if (e.key === " " && !e.target.closest("input, textarea, button, select")) { e.preventDefault(); $("[data-cc-play]").click(); }
  });

  window.__ccShorts = { exportMp4, renderAudio, st, tl };
  setFinish(st.finish);
  D.ready().then(() => draw(st.t));
})();
