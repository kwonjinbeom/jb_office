<?php
/**
 * Plugin Name: jinbaam 좋아요·공유
 * Description: 글 끝에 좋아요(로그인 없이 한 번)와 공유 줄. 파일 하나, 외부 서비스·추적 없음. 좋아요 수는 글 정보(_jb_likes)에 둔다.
 * Version: 1.3.0
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
        ? ['like' => 'Like', 'copy' => 'Copy link', 'done' => 'Link copied', 'kakao' => 'KakaoTalk', 'insta' => 'Instagram',
           'kdone' => 'Link copied · paste in KakaoTalk', 'idone' => 'Link copied · paste in a DM']
        : ['like' => '좋아요', 'copy' => '링크 복사', 'done' => '링크를 복사했어요', 'kakao' => '카카오톡', 'insta' => '인스타그램',
           'kdone' => '링크를 복사했어요 · 카톡에 붙여 넣기', 'idone' => '링크를 복사했어요 · DM 에 붙여 넣기'];
    // 아이콘만 (2026-10-28 사용자: 하트만, 버튼은 깔끔하고 간결하게). 브랜드 모양은 Simple Icons (CC0)
    $paths = [
        'kakaotalk' => 'M22.125 0H1.875C.8394 0 0 .8394 0 1.875v20.25C0 23.1606.8394 24 1.875 24h20.25C23.1606 24 24 23.1606 24 22.125V1.875C24 .8394 23.1606 0 22.125 0zM12 18.75c-.591 0-1.1697-.0413-1.7317-.1209-.5626.3965-3.813 2.6797-4.1198 2.7225 0 0-.1258.0489-.2328-.0141s-.0876-.2282-.0876-.2282c.0322-.2198.8426-3.0183.992-3.5333-2.7452-1.36-4.5701-3.7686-4.5701-6.5135C2.25 6.8168 6.6152 3.375 12 3.375s9.75 3.4418 9.75 7.6875c0 4.2457-4.3652 7.6875-9.75 7.6875zM8.0496 9.8672h-.8777v3.3417c0 .2963-.2523.5372-.5625.5372s-.5625-.2409-.5625-.5372V9.8672h-.8777c-.3044 0-.552-.2471-.552-.5508s.2477-.5508.552-.5508h2.8804c.3044 0 .552.2471.552.5508s-.2477.5508-.552.5508zm10.9879 2.9566a.558.558 0 0 1 .108.4167.5588.5588 0 0 1-.2183.371.5572.5572 0 0 1-.3383.1135.558.558 0 0 1-.4493-.2236l-1.3192-1.7479-.1952.1952v1.2273a.5635.5635 0 0 1-.5627.5628.563.563 0 0 1-.5625-.5625V9.3281c0-.3102.2523-.5625.5625-.5625s.5625.2523.5625.5625v1.209l1.5694-1.5694c.0807-.0807.1916-.1252.312-.1252.1404 0 .2814.0606.3871.1661.0985.0984.1573.2251.1654.3566.0082.1327-.036.2542-.1241.3425l-1.2818 1.2817 1.3845 1.8344zm-8.3502-3.5023c-.095-.2699-.3829-.5475-.7503-.5557-.3663.0083-.6542.2858-.749.5551l-1.3455 3.5415c-.1708.5305-.0217.7272.1333.7988a.8568.8568 0 0 0 .3576.0776c.2346 0 .4139-.0952.4678-.2481l.2787-.7297 1.7152.0001.2785.7292c.0541.1532.2335.2484.4681.2484a.8601.8601 0 0 0 .3576-.0775c.1551-.0713.3041-.2681.1329-.7999l-1.3449-3.5398zm-1.3116 2.4433l.5618-1.5961.5618 1.5961H9.3757zm5.9056 1.3836c0 .2843-.2418.5156-.5391.5156h-1.8047c-.2973 0-.5391-.2314-.5391-.5156V9.3281c0-.3102.2576-.5625.5742-.5625s.5742.2523.5742.5625v3.3047h1.1953c.2974 0 .5392.2314.5392.5156z',
        'instagram' => 'M7.0301.084c-1.2768.0602-2.1487.264-2.911.5634-.7888.3075-1.4575.72-2.1228 1.3877-.6652.6677-1.075 1.3368-1.3802 2.127-.2954.7638-.4956 1.6365-.552 2.914-.0564 1.2775-.0689 1.6882-.0626 4.947.0062 3.2586.0206 3.6671.0825 4.9473.061 1.2765.264 2.1482.5635 2.9107.308.7889.72 1.4573 1.388 2.1228.6679.6655 1.3365 1.0743 2.1285 1.38.7632.295 1.6361.4961 2.9134.552 1.2773.056 1.6884.069 4.9462.0627 3.2578-.0062 3.668-.0207 4.9478-.0814 1.28-.0607 2.147-.2652 2.9098-.5633.7889-.3086 1.4578-.72 2.1228-1.3881.665-.6682 1.0745-1.3378 1.3795-2.1284.2957-.7632.4966-1.636.552-2.9124.056-1.2809.0692-1.6898.063-4.948-.0063-3.2583-.021-3.6668-.0817-4.9465-.0607-1.2797-.264-2.1487-.5633-2.9117-.3084-.7889-.72-1.4568-1.3876-2.1228C21.2982 1.33 20.628.9208 19.8378.6165 19.074.321 18.2017.1197 16.9244.0645 15.6471.0093 15.236-.005 11.977.0014 8.718.0076 8.31.0215 7.0301.0839m.1402 21.6932c-1.17-.0509-1.8053-.2453-2.2287-.408-.5606-.216-.96-.4771-1.3819-.895-.422-.4178-.6811-.8186-.9-1.378-.1644-.4234-.3624-1.058-.4171-2.228-.0595-1.2645-.072-1.6442-.079-4.848-.007-3.2037.0053-3.583.0607-4.848.05-1.169.2456-1.805.408-2.2282.216-.5613.4762-.96.895-1.3816.4188-.4217.8184-.6814 1.3783-.9003.423-.1651 1.0575-.3614 2.227-.4171 1.2655-.06 1.6447-.072 4.848-.079 3.2033-.007 3.5835.005 4.8495.0608 1.169.0508 1.8053.2445 2.228.408.5608.216.96.4754 1.3816.895.4217.4194.6816.8176.9005 1.3787.1653.4217.3617 1.056.4169 2.2263.0602 1.2655.0739 1.645.0796 4.848.0058 3.203-.0055 3.5834-.061 4.848-.051 1.17-.245 1.8055-.408 2.2294-.216.5604-.4763.96-.8954 1.3814-.419.4215-.8181.6811-1.3783.9-.4224.1649-1.0577.3617-2.2262.4174-1.2656.0595-1.6448.072-4.8493.079-3.2045.007-3.5825-.006-4.848-.0608M16.953 5.5864A1.44 1.44 0 1 0 18.39 4.144a1.44 1.44 0 0 0-1.437 1.4424M5.8385 12.012c.0067 3.4032 2.7706 6.1557 6.173 6.1493 3.4026-.0065 6.157-2.7701 6.1506-6.1733-.0065-3.4032-2.771-6.1565-6.174-6.1498-3.403.0067-6.156 2.771-6.1496 6.1738M8 12.0077a4 4 0 1 1 4.008 3.9921A3.9996 3.9996 0 0 1 8 12.0077',
        'facebook' => 'M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z',
        'x' => 'M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.154h7.594l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z',
        'line' => 'M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.63-.63h2.386c.346 0 .627.285.627.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.63-.63.346 0 .628.285.628.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314',
        'pinterest' => 'M12.017 0C5.396 0 .029 5.367.029 11.987c0 5.079 3.158 9.417 7.618 11.162-.105-.949-.199-2.403.041-3.439.219-.937 1.406-5.957 1.406-5.957s-.359-.72-.359-1.781c0-1.663.967-2.911 2.168-2.911 1.024 0 1.518.769 1.518 1.688 0 1.029-.653 2.567-.992 3.992-.285 1.193.6 2.165 1.775 2.165 2.128 0 3.768-2.245 3.768-5.487 0-2.861-2.063-4.869-5.008-4.869-3.41 0-5.409 2.562-5.409 5.199 0 1.033.394 2.143.889 2.741.099.12.112.225.085.345-.09.375-.293 1.199-.334 1.363-.053.225-.172.271-.401.165-1.495-.69-2.433-2.878-2.433-4.646 0-3.776 2.748-7.252 7.92-7.252 4.158 0 7.392 2.967 7.392 6.923 0 4.135-2.607 7.462-6.233 7.462-1.214 0-2.354-.629-2.758-1.379l-.749 2.848c-.269 1.045-1.004 2.352-1.498 3.146 1.123.345 2.306.535 3.55.535 6.607 0 11.985-5.365 11.985-11.987C23.97 5.39 18.592.026 11.985.026L12.017 0z',
    ];
    $svg = function ($k) use ($paths) {
        if ($k === 'link') {  // 선 아이콘 (Feather, MIT)
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
    // 카카오톡 · 인스타그램은 웹 공유 링크가 없어 버튼으로 (아래 스크립트: 휴대폰은 공유 창, PC 는 카카오 SDK 또는 링크 복사)
    $share = $b('kakaotalk', 'jb-kakao', $t['kakao'], $t['kdone'])
        . $b('instagram', 'jb-insta', $t['insta'], $t['idone'])
        . $a('facebook', 'Facebook', "https://www.facebook.com/sharer/sharer.php?u={$url}")
        . $a('x', 'X', "https://twitter.com/intent/tweet?url={$url}&text={$title}")
        . $a('line', 'LINE', "https://social-plugins.line.me/lineit/share?url={$url}");
    if ($img) {
        $share .= $a('pinterest', 'Pinterest', "https://www.pinterest.com/pin/create/button/?url={$url}&media=" . rawurlencode($img) . "&description={$title}");
    }
    $share .= $b('link', 'jb-copy', $t['copy'], $t['done']);
    $heart = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5s-7.2-4.4-9.5-8.9C1 8.6 2.7 5 6.1 4.5c2-.3 3.8.7 4.8 2.3L12 8.4l1.1-1.6c1-1.6 2.8-2.6 4.8-2.3 3.4.5 5.1 4.1 3.6 7.1-2.3 4.5-9.5 8.9-9.5 8.9z"/></svg>';
    $count = (int) get_post_meta($id, JB_REACT_META, true);
    return $html
        . '<div class="jb-react" data-id="' . $id . '" data-api="' . esc_url(rest_url('jb/v1/like/' . $id)) . '"'
        . ' data-url="' . esc_url(get_permalink($id)) . '" data-title="' . esc_attr(wp_strip_all_tags(get_the_title($id))) . '"'
        . ' data-kakao="' . esc_attr(get_option('jb_react_kakao_key', '')) . '">'
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
.jb-react button{font:inherit;cursor:pointer}
.jb-like,.jb-ic{display:inline-flex;align-items:center;justify-content:center;padding:0;border:0;background:none;color:var(--jr-ink-3)}
.jb-like{gap:6px}
.jb-like svg{width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:1.6;transition:transform .15s}
.jb-like:hover{color:var(--jr-accent)}
.jb-like.on{color:var(--jr-accent);cursor:default}
.jb-like.on svg{fill:currentColor;transform:scale(1.08)}
.jb-like-n{font-family:var(--d-mono,ui-monospace,monospace);font-size:13px;font-weight:500}
.jb-like-n:empty{display:none}
.jb-msg{flex:1;min-width:0;color:var(--jr-accent);font-family:var(--d-sans,inherit);font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.jb-msg:empty{display:none}
.jb-share-row{display:flex;align-items:center;gap:16px;margin-left:auto}
.jb-ic{width:20px;height:20px}
.jb-ic svg{width:18px;height:18px;fill:currentColor}
.jb-ic svg.jb-st{fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.jb-ic:hover,.jb-ic:focus-visible,.jb-ic.done{color:var(--jr-accent)}
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
  // 공유 (2026-10-28 사용자: 카카오톡·인스타그램을 휴대폰과 PC 모두). 둘 다 웹 공유 링크가 없다.
  // 휴대폰: 폰의 공유 창 (카카오톡·인스타그램·문자 …). PC: 카카오톡은 카카오 공유 창(설정 › 일반 의 카카오 JavaScript 키가 있을 때) ·
  // 없으면 링크 복사, 인스타그램은 링크 복사 뒤 인스타그램 DM 을 연다 (인스타그램은 웹에서 글에 링크를 붙일 수 없다).
  var link = box.getAttribute("data-url"), title = box.getAttribute("data-title"), kakaoKey = box.getAttribute("data-kakao");
  var touch = !!(navigator.share && window.matchMedia && matchMedia("(pointer: coarse)").matches);
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
