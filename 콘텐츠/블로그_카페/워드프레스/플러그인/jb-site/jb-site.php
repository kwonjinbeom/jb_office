<?php
/**
 * Plugin Name: jinbaam 사이트 기본
 * Description: http → https 이동, /ads.txt (애드센스 게시자 ID 로). 애드센스 코드는 Site Kit 이 넣는다. 파일 하나.
 * Version: 1.1.0
 * Author: jinbaam
 * License: GPL-2.0-or-later
 *
 * 2026-10-28 사용자: 애드센스 신청 준비. http 주소도 그대로 열려 같은 글이 두 주소로 보였다 (카페24 openresty 뒤에서도
 * is_ssl() 이 http·https 를 바르게 가른다 — 확인함).
 * 1.1.0: Site Kit by Google 이 애드센스 코드·확인 meta 를 이미 넣고 있어서 이 플러그인은 코드를 넣지 않는다 (두 번 들어가지 않게).
 * ads.txt 는 Site Kit 이 만들지 않아 여기서 낸다. 저장소: 콘텐츠/블로그_카페/워드프레스/플러그인/
 */

if (!defined('ABSPATH')) {
    exit;
}

const JB_SITE_PUB = 'jb_adsense_pub';
const JB_SITE_PUB_DEFAULT = '5626348984264817';  // Site Kit 에 연결된 jinbaam.com 애드센스 계정 (2026-10-28 화면에서 읽음)

// http 로 온 화면은 같은 주소의 https 로 (관리자 화면은 건드리지 않는다 — 문제가 생겨도 플러그인을 끌 수 있게)
add_action('template_redirect', function () {
    if (is_ssl() || wp_doing_ajax() || (defined('WP_CLI') && WP_CLI)) {
        return;
    }
    $host = wp_parse_url(home_url(), PHP_URL_HOST);
    $uri = isset($_SERVER['REQUEST_URI']) ? (string) $_SERVER['REQUEST_URI'] : '/';
    wp_redirect('https://' . $host . $uri, 301);
    exit;
}, 1);

// 게시자 ID 숫자만: 설정 › 일반 칸 → Site Kit 애드센스 설정 → 기본값 순
function jb_site_pub()
{
    $kit = get_option('googlesitekit_adsense_settings');
    foreach ([get_option(JB_SITE_PUB, ''), is_array($kit) ? ($kit['accountID'] ?? '') : '', JB_SITE_PUB_DEFAULT] as $raw) {
        $id = preg_replace('/\D/', '', (string) $raw);
        if (strlen($id) >= 10) {
            return $id;
        }
    }
    return '';
}

add_action('admin_init', function () {
    register_setting('general', JB_SITE_PUB, ['type' => 'string', 'sanitize_callback' => 'sanitize_text_field', 'default' => '']);
    add_settings_field(JB_SITE_PUB, '애드센스 게시자 ID', function () {
        printf('<input name="%1$s" id="%1$s" type="text" class="regular-text code" value="%2$s" placeholder="ca-pub-%3$s">'
            . '<p class="description">비워 두면 Site Kit 에 연결된 계정을 쓴다. /ads.txt 에 이 ID 한 줄이 나간다.</p>',
            esc_attr(JB_SITE_PUB), esc_attr(get_option(JB_SITE_PUB, '')), esc_attr(jb_site_pub()));
    }, 'general');
});

// /ads.txt — 파일이 없으면 워드프레스가 받아서 404 를 내던 주소
add_action('init', function () {
    $path = isset($_SERVER['REQUEST_URI']) ? wp_parse_url((string) $_SERVER['REQUEST_URI'], PHP_URL_PATH) : '';
    if ($path !== '/ads.txt') {
        return;
    }
    $id = jb_site_pub();
    if (!$id) {
        return;
    }
    header('Content-Type: text/plain; charset=utf-8');
    header('Cache-Control: public, max-age=3600');
    echo "google.com, pub-{$id}, DIRECT, f08c47fec0942fa0\n";
    exit;
}, 0);
