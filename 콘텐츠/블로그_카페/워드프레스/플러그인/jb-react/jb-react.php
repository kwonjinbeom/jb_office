<?php
/**
 * Plugin Name: jinbaam 좋아요·공유
 * Description: 글 끝에 좋아요(로그인 없이 한 번)와 공유 줄. 파일 하나, 외부 서비스·추적 없음. 좋아요 수는 글 정보(_jb_likes)에 둔다.
 * Version: 1.4.0
 * Author: jinbaam
 * License: GPL-2.0-or-later
 *
 * 2026-10-28 사용자: 워드프레스에는 공감·좋아요가 없다 → 아주 가벼운 좋아요 + 공유 버튼.
 * 모양은 사이트.css 의 걷기 일기장(크림 종이 · 가는 먹선 · 벽돌색 날짜)을 따른다. 저장소: 콘텐츠/블로그_카페/워드프레스/플러그인/
 */

if (!defined('ABSPATH')) {
    exit;
}

const JB_REACT_META = '_jb_likes';

add_action('rest_api_init', function () {
    register_rest_route('jb/v1', '/like/(?P<id>\d+)', [
        ['methods' => 'GET', 'callback' => 'jb_react_count', 'permission_callback' => '__return_true'],
        ['methods' => 'POST', 'callback' => 'jb_react_like', 'permission_callback' => '__return_true'],
    ]);
});

function jb_react_post_ok($id)
{
    $post = get_post($id);
    return $post && $post->post_type === 'post' && $post->post_status === 'publish';
}

function jb_react_count($req)
{
    $id = (int) $req['id'];
    if (!jb_react_post_ok($id)) {
        return new WP_Error('jb_react_no_post', 'no post', ['status' => 404]);
    }
    return ['count' => (int) get_post_meta($id, JB_REACT_META, true)];
}

// 한 사람(IP)이 한 글에 하루 한 번만 센다. 브라우저도 눌렀던 글을 기억해 버튼을 다시 누를 수 없게 한다.
function jb_react_like($req)
{
    $id = (int) $req['id'];
    if (!jb_react_post_ok($id)) {
        return new WP_Error('jb_react_no_post', 'no post', ['status' => 404]);
    }
    $count = (int) get_post_meta($id, JB_REACT_META, true);
    $ip = isset($_SERVER['REMOTE_ADDR']) ? (string) $_SERVER['REMOTE_ADDR'] : '';
    $key = 'jb_like_' . md5($id . '|' . $ip . '|' . wp_salt('nonce'));
    if (!get_transient($key)) {
        set_transient($key, 1, DAY_IN_SECONDS);
        $count++;
        update_post_meta($id, JB_REACT_META, $count);
    }
    return ['count' => $count];
}

function jb_react_is_target()
{
    return is_singular('post') && in_the_loop() && is_main_query();
}

add_filter('the_content', function ($html) {
    if (!jb_react_is_target()) {
        return $html;
    }
    $id = get_the_ID();
    $en = strpos($html, 'lang="en"') !== false;  // 영어 카테고리 글 (Korea Travel · World Travel)
    $url = rawurlencode(get_permalink($id));
    $title = rawurlencode(wp_strip_all_tags(get_the_title($id)));
    $img = get_the_post_thumbnail_url($id, 'large');
    $t = $en
        ? ['like' => 'Like', 'copy' => 'Copy link', 'done' => 'Link copied']
        : ['like' => '좋아요', 'copy' => '링크 복사', 'done' => '링크를 복사했어요'];
    // 아이콘만 (2026-10-28 사용자: 하트만, 버튼은 깔끔하고 간결하게). 브랜드 모양은 Simple Icons (CC0)
    $paths = [
        'facebook' => 'M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z',
        'x' => 'M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.154h7.594l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z',
        'line' => 'M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.63-.63h2.386c.346 0 .627.285.627.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.63-.63.346 0 .628.285.628.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314',
        'pinterest' => 'M12.017 0C5.396 0 .029 5.367.029 11.987c0 5.079 3.158 9.417 7.618 11.162-.105-.949-.199-2.403.041-3.439.219-.937 1.406-5.957 1.406-5.957s-.359-.72-.359-1.781c0-1.663.967-2.911 2.168-2.911 1.024 0 1.518.769 1.518 1.688 0 1.029-.653 2.567-.992 3.992-.285 1.193.6 2.165 1.775 2.165 2.128 0 3.768-2.245 3.768-5.487 0-2.861-2.063-4.869-5.008-4.869-3.41 0-5.409 2.562-5.409 5.199 0 1.033.394 2.143.889 2.741.099.12.112.225.085.345-.09.375-.293 1.199-.334 1.363-.053.225-.172.271-.401.165-1.495-.69-2.433-2.878-2.433-4.646 0-3.776 2.748-7.252 7.92-7.252 4.158 0 7.392 2.967 7.392 6.923 0 4.135-2.607 7.462-6.233 7.462-1.214 0-2.354-.629-2.758-1.379l-.749 2.848c-.269 1.045-1.004 2.352-1.498 3.146 1.123.345 2.306.535 3.55.535 6.607 0 11.985-5.365 11.985-11.987C23.97 5.39 18.592.026 11.985.026L12.017 0z',
    ];
    $svg = function ($k) use ($paths) {
        if ($k === 'link') {  // 선 아이콘 (Lucide link, ISC)
            return '<svg class="jb-st" viewBox="0 0 24 24" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
                . '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>';
        }
        return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' . $paths[$k] . '"/></svg>';
    };
    $a = function ($k, $name, $href) use ($svg) {
        return '<a class="jb-ic" href="' . esc_url($href) . '" target="_blank" rel="noopener nofollow" title="' . esc_attr($name) . '" aria-label="' . esc_attr($name) . '">' . $svg($k) . '</a>';
    };
    $b = function ($k, $cls, $name, $done) use ($svg) {
        return '<button type="button" class="jb-ic ' . $cls . '" title="' . esc_attr($name) . '" aria-label="' . esc_attr($name) . '" data-done="' . esc_attr($done) . '">' . $svg($k) . '</button>';
    };
    // 카카오톡 · 인스타그램은 뺐다 (2026-10-28 사용자: 눌러도 안 되는 것은 지운다 — 둘 다 웹 공유 링크가 없어 링크 복사뿐이었다)
    $share = $a('facebook', 'Facebook', "https://www.facebook.com/sharer/sharer.php?u={$url}")
        . $a('x', 'X', "https://twitter.com/intent/tweet?url={$url}&text={$title}")
        . $a('line', 'LINE', "https://social-plugins.line.me/lineit/share?url={$url}");
    if ($img) {
        $share .= $a('pinterest', 'Pinterest', "https://www.pinterest.com/pin/create/button/?url={$url}&media=" . rawurlencode($img) . "&description={$title}");
    }
    $share .= $b('link', 'jb-copy', $t['copy'], $t['done']);
    // 하트는 Lucide heart (ISC, 2026-10-28 사용자가 고름)
    $heart = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5"/></svg>';
    $count = (int) get_post_meta($id, JB_REACT_META, true);
    return $html
        . '<div class="jb-react" data-id="' . $id . '" data-api="' . esc_url(rest_url('jb/v1/like/' . $id)) . '"'
        . ' data-url="' . esc_url(get_permalink($id)) . '">'
        . '<button type="button" class="jb-like" aria-pressed="false" title="' . esc_attr($t['like']) . '" aria-label="' . esc_attr($t['like']) . '">' . $heart
        . '<b class="jb-like-n">' . ($count > 0 ? $count : '') . '</b></button>'
        . '<span class="jb-msg" aria-live="polite"></span>'
        . '<div class="jb-share-row">' . $share . '</div></div>';
}, 20);

add_action('wp_footer', function () {
    if (!is_singular('post')) {
        return;
    }
    ?>
<style id="jb-react-css">
.jb-react{--jr-ink-3:var(--d-ink-3,#8f887d);--jr-line:var(--d-line,#ddd5c6);--jr-accent:var(--d-date,#a0522d);
  display:flex;align-items:center;gap:12px;margin:48px 0 0;padding-top:16px;border-top:1px solid var(--jr-line);line-height:1}
.jb-react button,.jb-react button:hover,.jb-react button:focus,.jb-react button:active{background:none!important;border:0!important;
  box-shadow:none!important;border-radius:0;padding:0;outline:none;font:inherit;cursor:pointer;-webkit-tap-highlight-color:transparent}
.jb-react button:focus-visible{outline:1px solid var(--jr-line)!important;outline-offset:4px}
.jb-react .jb-like,.jb-react .jb-ic{display:inline-flex;align-items:center;justify-content:center;color:var(--jr-ink-3)}
.jb-like{gap:6px}
.jb-like svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;transition:transform .15s}
.jb-react .jb-like:hover{color:var(--jr-accent)}
.jb-react .jb-like.on{color:var(--jr-accent);cursor:default}
.jb-like.on svg{fill:currentColor;transform:scale(1.08)}
.jb-like-n{font-family:var(--d-mono,ui-monospace,monospace);font-size:13px;font-weight:500}
.jb-like-n:empty{display:none}
.jb-msg{flex:1;min-width:0;color:var(--jr-accent);font-family:var(--d-sans,inherit);font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.jb-msg:empty{display:none}
.jb-share-row{display:flex;align-items:center;gap:16px;margin-left:auto}
.jb-ic{width:20px;height:20px}
.jb-ic svg{width:18px;height:18px;fill:currentColor}
.jb-ic svg.jb-st{fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.jb-react .jb-ic:hover,.jb-react .jb-ic:focus-visible,.jb-react .jb-ic.done{color:var(--jr-accent)}
@media (max-width:560px){.jb-react{flex-wrap:wrap}.jb-share-row{gap:14px}.jb-msg{order:3;flex-basis:100%;white-space:normal}}
</style>
<script id="jb-react-js">
(function () {
  var box = document.querySelector(".jb-react");
  if (!box) return;
  var api = box.getAttribute("data-api"), key = "jb_like_" + box.getAttribute("data-id");
  var btn = box.querySelector(".jb-like"), num = box.querySelector(".jb-like-n");
  function show(n, on) {
    num.textContent = n > 0 ? n : "";
    if (on) { btn.classList.add("on"); btn.setAttribute("aria-pressed", "true"); }
  }
  var liked = false;
  try { liked = localStorage.getItem(key) === "1"; } catch (e) {}
  if (liked) show(+num.textContent || 0, true);
  if (window.fetch) {  // 캐시된 화면의 숫자를 지금 숫자로
    fetch(api).then(function (r) { return r.json(); }).then(function (d) { show(d.count, liked); }).catch(function () {});
  }
  btn.addEventListener("click", function () {
    if (btn.classList.contains("on")) return;
    liked = true;
    show((+num.textContent || 0) + 1, true);
    try { localStorage.setItem(key, "1"); } catch (e) {}
    if (window.fetch) fetch(api, { method: "POST" }).then(function (r) { return r.json(); }).then(function (d) { show(d.count, true); }).catch(function () {});
  });
  var link = box.getAttribute("data-url");
  var msg = box.querySelector(".jb-msg"), msgTimer;
  function flash(el) {  // 아이콘만이라, 복사했다는 말은 하트 옆 한 줄로 잠깐
    el.classList.add("done"); msg.textContent = el.getAttribute("data-done");
    clearTimeout(msgTimer);
    msgTimer = setTimeout(function () { el.classList.remove("done"); msg.textContent = ""; }, 2500);
  }
  function copyOld() {  // 클립보드 권한이 막힌 곳(틀 안 · 옛 브라우저)에서
    var ta = document.createElement("textarea"), ok = false;
    ta.value = link; ta.setAttribute("readonly", ""); ta.style.cssText = "position:fixed;top:0;left:0;opacity:0";
    document.body.appendChild(ta); ta.select();
    try { ok = document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
    return ok;
  }
  function copyLink(el, then) {
    function done() { flash(el); if (then) then(); }
    function old() { copyOld() ? done() : window.prompt("", link); }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(link).then(done, old);
    else old();
  }
  var copy = box.querySelector(".jb-copy");
  copy.addEventListener("click", function () { copyLink(copy); });
})();
</script>
    <?php
});
