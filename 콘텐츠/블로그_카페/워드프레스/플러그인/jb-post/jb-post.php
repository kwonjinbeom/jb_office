<?php
/**
 * Plugin Name: jinbaam 글 화면
 * Description: 글 맨 위는 대표 사진 머리(흐린 사진 바탕 · 제목 · 사진, 메뉴는 그 위에 투명하게), 본문은 크림 종이, 글 끝(좋아요 줄부터)은 모래색 종이. 파일 하나.
 * Version: 1.0.0
 * Author: jinbaam
 * License: GPL-2.0-or-later
 *
 * 2026-10-28 사용자: 글마다 대표 사진이 맨 위까지 이어지게, Sources 까지는 원래 크림, 그 아래는 모래색(도안 C)으로.
 * 테마 GeneratePress 3.3.1 의 훅을 쓴다 (generate_before_content · generate_show_entry_header · generate_after_entry_content ·
 * generate_after_do_template_part). 좋아요·공유 줄은 jb-react 플러그인이 낸다. 저장소: 콘텐츠/블로그_카페/워드프레스/플러그인/
 */

if (!defined('ABSPATH')) {
    exit;
}

function jb_post_on()
{
    return is_singular('post');
}

// Lucide (ISC) — 카테고리 아이콘
function jb_post_icon($slug)
{
    $paths = [
        'mountain-camping' => '<path d="M3.5 21 14 3"/><path d="M20.5 21 10 3"/><path d="M15.5 21 12 15l-3.5 6"/><path d="M2 21h20"/>',
        'drive-car' => '<path d="m21 8-2 2-1.5-3.7A2 2 0 0 0 15.646 5H8.4a2 2 0 0 0-1.903 1.257L5 10 3 8"/><path d="M7 14h.01"/><path d="M17 14h.01"/><rect width="18" height="8" x="3" y="10" rx="2"/><path d="M5 18v2"/><path d="M19 18v2"/>',
        'korea-travel' => '<path d="M10 18v-7"/><path d="M11.119 2.205a2 2 0 0 1 1.762 0l7.84 3.846A.5.5 0 0 1 20.5 7h-17a.5.5 0 0 1-.22-.949z"/><path d="M14 18v-7"/><path d="M18 18v-7"/><path d="M3 22h18"/><path d="M6 18v-7"/>',
        'world-travel' => '<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>',
    ];
    $p = $paths[$slug] ?? '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>';
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' . $p . '</svg>';
}

// 테마의 대표 이미지 · 제목 머리 · 글자 이전/다음 대신 이 플러그인 것을 쓴다
add_action('wp', function () {
    if (!jb_post_on()) {
        return;
    }
    remove_action('generate_before_content', 'generate_featured_page_header_inside_single', 10);
    add_filter('generate_show_entry_header', '__return_false');
    add_filter('generate_show_post_navigation', '__return_false');
});

// 맨 위 머리: 흐린 대표 사진 바탕 · 카테고리 · 제목 · 날짜 · 대표 사진
add_action('generate_before_content', function () {
    if (!jb_post_on()) {
        return;
    }
    $id = get_the_ID();
    $img = get_the_post_thumbnail_url($id, 'large');
    $cat = get_the_category($id);
    $cat = $cat ? $cat[0] : null;
    echo '<div class="jb-hero' . ($img ? '' : ' jb-hero--plain') . '"' . ($img ? ' style="--jb-feat:url(\'' . esc_url($img) . '\')"' : '') . '><div class="jb-hero-in"><div class="jb-hero-text">';
    if ($cat) {
        printf('<a class="jb-hero-cat" href="%s"><span>%s</span>%s</a>', esc_url(get_category_link($cat)), jb_post_icon($cat->slug), esc_html($cat->name));
    }
    printf('<h1 class="entry-title jb-hero-title" itemprop="headline">%s</h1>', esc_html(get_the_title($id)));
    printf('<p class="jb-hero-date"><time datetime="%s" itemprop="datePublished">%s</time></p></div>', esc_attr(get_the_date('c', $id)), esc_html(get_the_date('Y.m.d', $id)));
    if ($img) {
        echo '<figure class="jb-hero-img">' . get_the_post_thumbnail($id, 'large', ['loading' => false, 'fetchpriority' => 'high', 'decoding' => 'async']) . '</figure>';
    }
    echo '</div></div>';
}, 10);

// 본문 첫 사진이 대표 사진과 같으면 본문에서는 뺀다 (머리에 이미 있다)
add_filter('the_content', function ($html) {
    if (!jb_post_on() || !in_the_loop() || !is_main_query()) {
        return $html;
    }
    $src = get_the_post_thumbnail_url(get_the_ID(), 'full');
    if (!$src) {
        return $html;
    }
    $base = preg_replace('/(-\d+x\d+)?\.[a-z0-9]+$/i', '', wp_basename(wp_parse_url($src, PHP_URL_PATH)));
    if (strlen($base) < 4) {
        return $html;
    }
    $re = '~<figure\b[^>]*>(?:(?!</figure>).)*?/' . preg_quote($base, '~') . '(?:-\d+x\d+)?\.[a-z0-9]+["\'?](?:(?!</figure>).)*</figure>~is';
    return preg_replace($re, '', $html, 1);
}, 9);

// Filed under 아래: 이전 · 다음 기록 카드 (작은 사진)
add_action('generate_after_entry_content', function () {
    if (!jb_post_on()) {
        return;
    }
    $cards = '';
    foreach ([[get_previous_post(), '← 이전 기록', 'jb-card'], [get_next_post(), '다음 기록 →', 'jb-card jb-card--next']] as [$p, $label, $cls]) {
        if (!$p) {
            $cards .= '<span></span>';
            continue;
        }
        $thumb = get_the_post_thumbnail($p, 'thumbnail', ['loading' => 'lazy', 'alt' => '']);
        $text = '<span class="jb-card-t"><i>' . $label . '</i>' . esc_html(get_the_title($p)) . '</span>';
        $cards .= sprintf('<a class="%s%s" href="%s">%s</a>', $cls, $thumb ? '' : ' jb-card--text', esc_url(get_permalink($p)),
            $cls === 'jb-card' ? $thumb . $text : $text . $thumb);
    }
    echo '<nav class="jb-nav" aria-label="Posts">' . $cards . '</nav>';
}, 20);

// 댓글 아래: 일기장 서명 · 카테고리 · 바닥 줄 (글 화면에서는 테마 바닥 대신)
add_action('generate_after_do_template_part', function ($template) {
    if ($template !== 'single' || !jb_post_on()) {
        return;
    }
    $cats = '';
    foreach (['mountain-camping', 'drive-car', 'korea-travel', 'world-travel'] as $slug) {
        $c = get_category_by_slug($slug);
        if ($c) {
            $cats .= sprintf('<a href="%s">%s%s</a>', esc_url(get_category_link($c)), jb_post_icon($slug), esc_html($c->name));
        }
    }
    $links = [];
    foreach (['about' => 'About', 'contact' => 'Contact', 'privacy-policy' => 'Privacy'] as $slug => $name) {
        if (get_page_by_path($slug)) {
            $links[] = sprintf('<a href="%s">%s</a>', esc_url(home_url('/' . $slug . '/')), $name);
        }
    }
    echo '<div class="jb-sign"><div><p class="jb-sign-t">걸어온 길, 적어 둔 날들</p><p class="jb-sign-e">Roads I’ve walked, days I’ve written down.</p></div>'
        . '<nav class="jb-sign-cats" aria-label="Categories">' . $cats . '</nav></div>'
        . '<p class="jb-foot">© ' . esc_html(wp_date('Y')) . ' ' . esc_html(get_bloginfo('name')) . ($links ? ' · ' . implode(' · ', $links) : '') . '</p>';
}, 20);

add_action('wp_head', function () {
    if (!jb_post_on()) {
        return;
    }
    ?>
<style id="jb-post-css">
/* 틀: 머리는 사진 위에 투명하게, 바탕은 모래색 종이 · 본문만 크림 종이 */
html:has(body.single-post) { overflow-x: clip; }
body.single-post { --jb-sand: #ebe2d2; --jb-sand-line: #d8ccb8; --jb-amber: #c7782a; background: var(--jb-sand); }
.single-post .site-header { position: absolute; left: 0; right: 0; top: 0; z-index: 30; background: transparent; border-bottom: 1px solid rgba(255, 255, 255, 0.2); -webkit-backdrop-filter: none; backdrop-filter: none; }
.admin-bar.single-post .site-header { top: 32px; }
.single-post .main-title a, .single-post .main-navigation .main-nav ul li a, .single-post .main-navigation .menu-toggle { color: #fff; text-shadow: 0 1px 8px rgba(0, 0, 0, 0.28); }
.single-post .main-navigation .main-nav ul li a:hover { color: #f2b25e; }
.single-post .main-navigation .main-nav ul li a[href*="/category/"]::before { color: #f2b25e; }
.single-post .main-navigation.toggled .main-nav ul li a { color: var(--d-ink); text-shadow: none; }
.separate-containers.single-post .site-main:not(#jb) { margin-top: 0; margin-bottom: 0; padding-bottom: 40px; }
.single-post .site-footer { display: none; }

/* 맨 위 머리 */
.jb-hero { position: relative; width: 100vw; margin: 0 0 0 calc(50% - 50vw); overflow: hidden; background: #141a3a; }
.jb-hero::before { content: ""; position: absolute; inset: -40px; background: var(--jb-feat) center / cover; filter: blur(30px) brightness(0.45) saturate(1.1); }
.jb-hero--plain::before { display: none; }
.jb-hero-in { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 44px; align-items: center; max-width: 980px; margin: 0 auto; padding: 130px 24px 56px; }
.jb-hero--plain .jb-hero-in { grid-template-columns: minmax(0, 1fr); max-width: 820px; }
.jb-hero-cat { display: inline-flex; align-items: center; gap: 8px; color: #f2b25e; font-family: var(--d-mono); font-size: 12.5px; letter-spacing: 0.06em; text-decoration: none; }
.jb-hero-cat:hover, .jb-hero-cat:focus { color: #fff; }
.jb-hero-cat span { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 8px; background: rgba(242, 178, 94, 0.16); }
.jb-hero-cat svg { width: 16px; height: 16px; }
.single-post .jb-hero .jb-hero-title { margin: 14px 0; color: #fff; font-family: var(--d-serif); font-size: 34px; font-weight: 700; line-height: 1.35; letter-spacing: -0.01em; }
.jb-hero-date { margin: 0; color: rgba(255, 255, 255, 0.7); font-family: var(--d-mono); font-size: 12.5px; }
.jb-hero-img { margin: 0; }
.jb-hero-img img { display: block; width: 100%; height: auto; aspect-ratio: 4 / 3; object-fit: cover; border-radius: 14px; box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35); }

/* 본문: 크림 종이 (화면 폭 가득) */
.single-post .inside-article > .entry-content:not(#jb) { margin-top: 0; padding: 44px 0 0; border-image: linear-gradient(var(--d-paper) 0 0) fill 0 / / 0 100vmax; }

/* 글 끝: 좋아요 줄부터 모래색 종이, 위에 먹선 한 줄 */
.single-post .entry-content .jb-react { margin: 48px 0 0; padding: 34px 0 0; border: 0; border-image: linear-gradient(var(--d-ink) 0 1px, var(--jb-sand) 1px) fill 0 / / 0 100vmax; --jr-ink-3: #6f675b; --jr-accent: var(--jb-amber); }
.single-post footer.entry-meta:not(#jb) { margin: 24px 0 0; padding: 0; border: 0; }
.single-post footer.entry-meta:not(#jb) .cat-links::before { position: static; width: auto; margin: 0; color: var(--jb-amber); }
.single-post .tags-links a { color: #7d7466; }
.single-post .tags-links a::before { color: #a99f90; }
.jb-nav { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 28px 0 0; }
.jb-card { display: grid; grid-template-columns: 84px minmax(0, 1fr); gap: 14px; align-items: center; padding: 12px; border: 1px solid var(--jb-sand-line); border-radius: 14px; background: var(--d-paper); color: var(--d-ink); font-family: var(--d-serif); font-size: 14.5px; font-weight: 700; line-height: 1.5; text-decoration: none; }
.jb-card--next { grid-template-columns: minmax(0, 1fr) 84px; text-align: right; }
.jb-card--text { grid-template-columns: minmax(0, 1fr); }
.jb-card:hover, .jb-card:focus { border-color: var(--d-ink); color: var(--d-ink); }
.jb-card img { display: block; width: 84px; height: 64px; object-fit: cover; border-radius: 9px; background: #fff; }
.jb-card i { display: block; margin-bottom: 4px; color: var(--jb-amber); font-family: var(--d-mono); font-size: 11.5px; font-style: normal; font-weight: 400; }
.separate-containers.single-post .comments-area:not(#jb) { margin: 36px 0 0; padding: 26px 0 0; border-top: 1px solid var(--jb-sand-line); }
.single-post .comment-form input:not([type="submit"]):not([type="checkbox"]), .single-post .comment-form textarea { border: 1px solid var(--jb-sand-line); border-radius: 10px; background: var(--d-paper); }
.single-post .comment-form textarea { height: 110px; }
.single-post .comment-form input[type="submit"] { padding: 10px 22px; border: 0; border-radius: 999px; background: var(--d-ink); color: var(--d-paper); font-weight: 700; }
.single-post .comment-form input[type="submit"]:hover { background: var(--jb-amber); }
.jb-sign { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; margin: 44px 0 0; padding-top: 22px; border-top: 1px solid var(--jb-sand-line); }
.jb-sign-t { margin: 0; color: var(--d-ink); font-family: var(--d-serif); font-size: 22px; font-weight: 700; }
.jb-sign-e { margin: 4px 0 0; color: #7d7466; font-family: Georgia, serif; font-size: 14px; font-style: italic; }
.jb-sign-cats { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px 18px; }
.jb-sign-cats a { display: inline-flex; align-items: center; gap: 6px; color: #3d3a35; font-size: 13px; text-decoration: none; }
.jb-sign-cats a:hover { color: var(--jb-amber); }
.jb-sign-cats svg { width: 15px; height: 15px; color: var(--jb-amber); }
.jb-foot { margin: 26px 0 0; color: #7d7466; font-family: var(--d-mono); font-size: 12px; }
.jb-foot a { color: inherit; }

@media (max-width: 768px) {
  .admin-bar.single-post .site-header { top: 46px; }
  .jb-hero-in { grid-template-columns: minmax(0, 1fr); gap: 20px; padding: 84px 16px 30px; }
  .jb-hero-img { order: -1; }
  .single-post .jb-hero .jb-hero-title { font-size: 25px; }
  .single-post .inside-article > .entry-content:not(#jb) { padding-top: 32px; }
  .jb-nav { grid-template-columns: 1fr; }
  .jb-sign { flex-direction: column; align-items: flex-start; }
  .jb-sign-cats { justify-content: flex-start; }
}
</style>
    <?php
}, 20);
