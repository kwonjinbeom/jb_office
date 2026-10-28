<?php
/**
 * Plugin Name: jinbaam 좋아요·공유
 * Description: 글 끝에 좋아요(로그인 없이 한 번)와 공유 줄. 파일 하나, 외부 서비스·추적 없음. 좋아요 수는 글 정보(_jb_likes)에 둔다.
 * Version: 1.2.0
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

// 카카오톡 공유 창 (PC 에서 친구·채팅방 고르기)에 쓰는 카카오 JavaScript 키. 비어 있으면 PC 의 카카오톡 버튼은 링크 복사.
// 설정 › 일반 맨 아래 칸, 또는 REST /wp/v2/settings 의 jb_react_kakao_key.
add_action('init', function () {
    register_setting('general', 'jb_react_kakao_key', [
        'type' => 'string',
        'default' => '',
        'show_in_rest' => true,
        'sanitize_callback' => function ($v) { return preg_replace('/[^A-Za-z0-9]/', '', (string) $v); },
    ]);
});

add_action('admin_init', function () {
    add_settings_field('jb_react_kakao_key', '카카오 JavaScript 키 (좋아요·공유)', function () {
        echo '<input type="text" class="regular-text code" name="jb_react_kakao_key" value="' . esc_attr(get_option('jb_react_kakao_key', '')) . '">'
            . '<p class="description">카카오 developers › 내 애플리케이션 › 앱 키의 JavaScript 키. 비우면 PC 의 카카오톡 버튼은 링크를 복사한다.</p>';
    }, 'general');
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
        ? ['like' => 'Like', 'share' => 'Share', 'copy' => 'Copy link', 'done' => 'Copied', 'kakao' => 'KakaoTalk', 'insta' => 'Instagram',
           'kdone' => 'Copied · paste in KakaoTalk', 'idone' => 'Copied · paste in a DM']
        : ['like' => '좋아요', 'share' => '공유', 'copy' => '링크 복사', 'done' => '복사했어요', 'kakao' => '카카오톡', 'insta' => '인스타그램',
           'kdone' => '복사했어요 · 카톡에 붙여 넣기', 'idone' => '복사했어요 · DM 에 붙여 넣기'];
    $link = function ($name, $href) {
        return '<a class="jb-share" href="' . esc_url($href) . '" target="_blank" rel="noopener nofollow">' . esc_html($name) . '</a>';
    };
    // 카카오톡 · 인스타그램은 웹 공유 링크가 없어 버튼으로 (아래 스크립트: 휴대폰은 공유 창, PC 는 카카오 SDK 또는 링크 복사)
    $share = $link('Facebook', "https://www.facebook.com/sharer/sharer.php?u={$url}")
        . $link('X', "https://twitter.com/intent/tweet?url={$url}&text={$title}")
        . '<button type="button" class="jb-share jb-kakao" data-done="' . esc_attr($t['kdone']) . '">' . esc_html($t['kakao']) . '</button>'
        . $link('LINE', "https://social-plugins.line.me/lineit/share?url={$url}")
        . '<button type="button" class="jb-share jb-insta" data-done="' . esc_attr($t['idone']) . '">' . esc_html($t['insta']) . '</button>';
    if ($img) {
        $share .= $link('Pinterest', "https://www.pinterest.com/pin/create/button/?url={$url}&media=" . rawurlencode($img) . "&description={$title}");
    }
    $heart = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5s-7.2-4.4-9.5-8.9C1 8.6 2.7 5 6.1 4.5c2-.3 3.8.7 4.8 2.3L12 8.4l1.1-1.6c1-1.6 2.8-2.6 4.8-2.3 3.4.5 5.1 4.1 3.6 7.1-2.3 4.5-9.5 8.9-9.5 8.9z"/></svg>';
    $count = (int) get_post_meta($id, JB_REACT_META, true);
    return $html
        . '<div class="jb-react" data-id="' . $id . '" data-api="' . esc_url(rest_url('jb/v1/like/' . $id)) . '"'
        . ' data-url="' . esc_url(get_permalink($id)) . '" data-title="' . esc_attr(wp_strip_all_tags(get_the_title($id))) . '"'
        . ' data-kakao="' . esc_attr(get_option('jb_react_kakao_key', '')) . '">'
        . '<button type="button" class="jb-like" aria-pressed="false">' . $heart . '<span>' . esc_html($t['like']) . '</span>'
        . '<b class="jb-like-n">' . ($count > 0 ? $count : '') . '</b></button>'
        . '<div class="jb-share-row"><span class="jb-share-label">' . esc_html($t['share']) . '</span>' . $share
        . '<button type="button" class="jb-share jb-copy" data-done="' . esc_attr($t['done']) . '">'
        . esc_html($t['copy']) . '</button></div></div>';
}, 20);

add_action('wp_footer', function () {
    if (!is_singular('post')) {
        return;
    }
    ?>
<style id="jb-react-css">
.jb-react{--jr-ink:var(--d-ink,#26231f);--jr-ink-3:var(--d-ink-3,#8f887d);--jr-line:var(--d-line,#ddd5c6);--jr-accent:var(--d-date,#a0522d);
  display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:12px 20px;margin:48px 0 0;padding-top:18px;border-top:1px solid var(--jr-line);
  font-family:var(--d-sans,inherit);font-size:14px;line-height:1.4}
.jb-react button{font:inherit;cursor:pointer}
.jb-like{display:inline-flex;align-items:center;gap:7px;height:38px;padding:0 16px;border:1px solid var(--jr-line);border-radius:999px;background:transparent;color:var(--jr-ink)}
.jb-like svg{width:17px;height:17px;fill:none;stroke:var(--jr-accent);stroke-width:1.8}
.jb-like:hover{border-color:var(--jr-accent)}
.jb-like.on{border-color:var(--jr-accent);color:var(--jr-accent);cursor:default}
.jb-like.on svg{fill:var(--jr-accent)}
.jb-like-n{min-width:0;font-family:var(--d-mono,ui-monospace,monospace);font-size:13px;font-weight:500;color:var(--jr-ink-3)}
.jb-like-n:empty{display:none}
.jb-like.on .jb-like-n{color:var(--jr-accent)}
.jb-share-row{display:flex;flex-wrap:wrap;align-items:center;gap:6px 16px}
.jb-share-label{color:var(--jr-accent);font-family:var(--d-mono,ui-monospace,monospace);font-size:12px}
.jb-share{padding:0;border:0;background:none;color:var(--jr-ink);font-size:13.5px;text-decoration:none;border-bottom:1px solid var(--jr-line)}
.jb-share:hover,.jb-share:focus{color:var(--jr-accent);border-bottom-color:var(--jr-accent)}
.jb-share.done{color:var(--jr-accent);border-bottom-color:var(--jr-accent)}
.jb-react [hidden]{display:none}
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
  // 공유 (2026-10-28 사용자: 카카오톡·인스타그램을 휴대폰과 PC 모두). 둘 다 웹 공유 링크가 없다.
  // 휴대폰: 폰의 공유 창 (카카오톡·인스타그램·문자 …). PC: 카카오톡은 카카오 공유 창(설정 › 일반 의 카카오 JavaScript 키가 있을 때) ·
  // 없으면 링크 복사, 인스타그램은 링크 복사 뒤 인스타그램 DM 을 연다 (인스타그램은 웹에서 글에 링크를 붙일 수 없다).
  var link = box.getAttribute("data-url"), title = box.getAttribute("data-title"), kakaoKey = box.getAttribute("data-kakao");
  var touch = !!(navigator.share && window.matchMedia && matchMedia("(pointer: coarse)").matches);
  function flash(el) {
    var label = el.getAttribute("data-label") || el.textContent;
    el.setAttribute("data-label", label);
    el.classList.add("done"); el.textContent = el.getAttribute("data-done");
    setTimeout(function () { el.classList.remove("done"); el.textContent = label; }, 2500);
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
  function phoneShare(el) {
    navigator.share({ title: title, url: link }).catch(function (e) { if (!e || e.name !== "AbortError") copyLink(el); });
  }
  var sdk = null;
  function kakaoSdk() {  // 한 번만 받는다
    return sdk || (sdk = new Promise(function (ok, no) {
      if (window.Kakao) return ok(window.Kakao);
      var s = document.createElement("script");
      s.src = "https://t1.kakaocdn.net/kakao_js_sdk/2.8.4/kakao.min.js";
      s.integrity = "sha384-BGX7Wb16GmRFagri4bLJV2DgipVZaU2AI812GZtHtHzzDQJnfHasDXN5houxv45w";
      s.crossOrigin = "anonymous";
      s.onload = function () { window.Kakao ? ok(window.Kakao) : no(); };
      s.onerror = no;
      document.head.appendChild(s);
    }));
  }
  if (kakaoKey) {  // 공유 줄에 손이 가면 미리 받아 둔다 — 누를 때 받으면 PC 의 카카오 공유 창이 팝업 차단에 걸릴 수 있다
    var warm = function () { kakaoSdk().catch(function () {}); box.removeEventListener("pointerover", warm); box.removeEventListener("touchstart", warm); };
    box.addEventListener("pointerover", warm);
    box.addEventListener("touchstart", warm, { passive: true });
  }
  var kakao = box.querySelector(".jb-kakao");
  kakao.addEventListener("click", function () {
    if (kakaoKey) {
      kakaoSdk().then(function (K) {
        if (!K.isInitialized()) K.init(kakaoKey);
        K.Share.sendScrap({ requestUrl: link });
      }).catch(function () { touch ? phoneShare(kakao) : copyLink(kakao); });
    } else if (touch) { phoneShare(kakao); } else { copyLink(kakao); }
  });
  var insta = box.querySelector(".jb-insta");
  insta.addEventListener("click", function () {
    if (touch) phoneShare(insta);
    else copyLink(insta, function () { window.open("https://www.instagram.com/direct/inbox/", "_blank", "noopener"); });
  });
  var copy = box.querySelector(".jb-copy");
  copy.addEventListener("click", function () { copyLink(copy); });
})();
</script>
    <?php
});
