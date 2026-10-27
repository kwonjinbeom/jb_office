<?php
/**
 * Plugin Name: jinbaam 좋아요·공유
 * Description: 글 끝에 좋아요(로그인 없이 한 번)와 공유 줄. 파일 하나, 외부 서비스·추적 없음. 좋아요 수는 글 정보(_jb_likes)에 둔다.
 * Version: 1.1.0
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
        ? ['like' => 'Like', 'share' => 'Share', 'copy' => 'Copy link', 'done' => 'Copied', 'more' => 'More']
        : ['like' => '좋아요', 'share' => '공유', 'copy' => '링크 복사', 'done' => '복사했어요', 'more' => '카톡·더보기'];
    $links = [
        'Facebook' => "https://www.facebook.com/sharer/sharer.php?u={$url}",
        'X' => "https://twitter.com/intent/tweet?url={$url}&text={$title}",
        'LINE' => "https://social-plugins.line.me/lineit/share?url={$url}",
    ];
    if ($img) {
        $links['Pinterest'] = "https://www.pinterest.com/pin/create/button/?url={$url}&media=" . rawurlencode($img) . "&description={$title}";
    }
    $share = '';
    foreach ($links as $name => $href) {
        $share .= '<a class="jb-share" href="' . esc_url($href) . '" target="_blank" rel="noopener nofollow">' . esc_html($name) . '</a>';
    }
    $heart = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5s-7.2-4.4-9.5-8.9C1 8.6 2.7 5 6.1 4.5c2-.3 3.8.7 4.8 2.3L12 8.4l1.1-1.6c1-1.6 2.8-2.6 4.8-2.3 3.4.5 5.1 4.1 3.6 7.1-2.3 4.5-9.5 8.9-9.5 8.9z"/></svg>';
    $count = (int) get_post_meta($id, JB_REACT_META, true);
    return $html
        . '<div class="jb-react" data-id="' . $id . '" data-api="' . esc_url(rest_url('jb/v1/like/' . $id)) . '">'
        . '<button type="button" class="jb-like" aria-pressed="false">' . $heart . '<span>' . esc_html($t['like']) . '</span>'
        . '<b class="jb-like-n">' . ($count > 0 ? $count : '') . '</b></button>'
        . '<div class="jb-share-row"><span class="jb-share-label">' . esc_html($t['share']) . '</span>' . $share
        . '<button type="button" class="jb-share jb-more" hidden data-title="' . esc_attr(wp_strip_all_tags(get_the_title($id))) . '">' . esc_html($t['more']) . '</button>'
        . '<button type="button" class="jb-share jb-copy" data-url="' . esc_url(get_permalink($id)) . '" data-done="' . esc_attr($t['done']) . '">'
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
.jb-copy.done{color:var(--jr-accent)}
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
  // 카카오톡·인스타그램은 웹 공유 링크가 없다 → 휴대폰 공유 창 (2026-10-28 사용자). 공유 창이 없는 PC 에서는 버튼을 숨긴 채 둔다
  var more = box.querySelector(".jb-more"), link = box.querySelector(".jb-copy").getAttribute("data-url");
  if (navigator.share) {
    more.hidden = false;
    more.addEventListener("click", function () { navigator.share({ title: more.getAttribute("data-title"), url: link }).catch(function () {}); });
  }
  var copy = box.querySelector(".jb-copy");
  copy.addEventListener("click", function () {
    var url = copy.getAttribute("data-url"), label = copy.textContent;
    function done() { copy.classList.add("done"); copy.textContent = copy.getAttribute("data-done"); setTimeout(function () { copy.classList.remove("done"); copy.textContent = label; }, 1800); }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(url).then(done, function () { window.prompt("", url); });
    else window.prompt("", url);
  });
})();
</script>
    <?php
});
