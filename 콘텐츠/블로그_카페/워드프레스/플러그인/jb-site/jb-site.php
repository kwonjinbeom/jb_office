<?php
/**
 * Plugin Name: jinbaam 사이트 기본
 * Description: http → https 이동, 애드센스 코드(설정 › 일반의 게시자 ID 하나), /ads.txt. 파일 하나.
 * Version: 1.0.0
 * Author: jinbaam
 * License: GPL-2.0-or-later
 *
 * 2026-10-28 사용자: 애드센스 신청 준비. http 주소도 그대로 열려 같은 글이 두 주소로 보였다 (카페24 openresty 뒤에서도
 * is_ssl() 이 http·https 를 바르게 가른다 — 확인함). 게시자 ID 를 넣기 전에는 애드센스 코드·ads.txt 가 나가지 않는다.
 * 저장소: 콘텐츠/블로그_카페/워드프레스/플러그인/
 */

if (!defined('ABSPATH')) {
    exit;
}

const JB_SITE_PUB = 'jb_adsense_pub';

// http 로 온 화면은 같은 주소의 https 로 (관리자 화면은 건드리지 않는다 — 문제가 생겨도 플러그인을 끌 수 있게)
add_action('template_redirect', function () {
    if (is_ssl() || is_admin() || wp_doing_ajax() || (defined('WP_CLI') && WP_CLI)) {
        return;
    }
    $host = wp_parse_url(home_url(), PHP_URL_HOST);
    $uri = isset($_SERVER['REQUEST_URI']) ? (string) $_SERVER['REQUEST_URI'] : '/';
    wp_redirect('https://' . $host . $uri, 301);
    exit;
}, 1);

// 게시자 ID: 'ca-pub-123…' · 'pub-123…' · 숫자만 다 받아 숫자 16자리만 남긴다
function jb_site_pub()
{
    $id = preg_replace('/\D/', '', (string) get_option(JB_SITE_PUB, ''));
    return strlen($id) >= 10 ? $id : '';
}

add_action('admin_init', function () {
    register_setting('general', JB_SITE_PUB, ['type' => 'string', 'sanitize_callback' => 'sanitize_text_field', 'default' => '']);
    add_settings_field(JB_SITE_PUB, '애드센스 게시자 ID', function () {
        printf('<input name="%1$s" id="%1$s" type="text" class="regular-text code" value="%2$s" placeholder="ca-pub-0000000000000000">'
            . '<p class="description">애드센스 › 계정 › 계정 정보의 게시자 ID. 넣으면 모든 화면에 애드센스 코드가, /ads.txt 에 한 줄이 나간다.</p>',
            esc_attr(JB_SITE_PUB), esc_attr(get_option(JB_SITE_PUB, '')));
    }, 'general');
});

add_action('wp_head', function () {
    $id = jb_site_pub();
    if (!$id) {
        return;
    }
    echo '<meta name="google-adsense-account" content="ca-pub-' . esc_attr($id) . '">' . "\n";
    echo '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-' . esc_attr($id)
        . '" crossorigin="anonymous"></script>' . "\n";
}, 1);

// /ads.txt — 파일이 없으면 워드프레스가 받아서 404 를 내던 주소. 게시자 ID 가 없으면 그대로 404.
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
