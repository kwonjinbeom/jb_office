from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.writing.models import Post as TistoryPost
from .forms import PostForm
from .models import Post
from .render import clean_html, paste_html, plain_text, render_body, QUOTE_STYLES, HR_STYLES


class NaverWorkflowTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("naver-test"))
        self.git = patch("apps.core.context_processors.gitstate.deploy_status", return_value=None)
        self.git.start()
        self.addCleanup(self.git.stop)

    def test_stage_lists_and_counts_are_independent_from_tistory(self):
        TistoryPost.objects.create(title="티스토리 전용 원고")
        for stage in Post.Stage:
            Post.objects.create(title=f"네이버 {stage}", stage=stage)
        for stage, name in [("temp", "list"), ("review", "review"), ("post", "posts")]:
            response = self.client.get(reverse(f"naver_writing:{name}"))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, f"네이버 {stage}")
            self.assertNotContains(response, "티스토리 전용 원고")
            self.assertEqual([t["count"] for t in response.context["tabs"]], [1, 1, 1])
        self.assertContains(response, "미작성")
        self.assertContains(response, "미발행")
        self.assertEqual(TistoryPost.objects.count(), 1)

    def test_create_edit_read_search_and_delete(self):
        response = self.client.post(reverse("naver_writing:create"), {
            "title": "네이버 새 원고", "summary": "검색용 요약", "tags": "#가을, 여행",
            "body": '<p style="text-align:center"><span style="font-size:19px;color:#123456">내용</span></p>',
        })
        post = Post.objects.get()
        self.assertRedirects(response, post.get_absolute_url())
        response = self.client.get(post.get_absolute_url())
        self.assertContains(response, "#가을")
        self.assertContains(response, "font-size:19px;color:#123456")
        self.assertNotContains(response, "복사해서 붙여넣기")  # 글 보기는 본문을 넓게 (복사 줄 없음)
        self.assertContains(response, 'data-paper-width="mobile"')  # PC·모바일은 단계 탭 줄에
        self.assertNotContains(response, "티스토리 HTML")
        self.assertContains(self.client.get(reverse("naver_writing:list"), {"q": "검색용"}), post.title)
        response = self.client.post(reverse("naver_writing:edit", args=[post.pk]), {
            "title": "수정 원고", "body": "## 소제목\n\n본문", "tags": "새태그",
        })
        self.assertRedirects(response, post.get_absolute_url())
        self.assertContains(self.client.get(post.get_absolute_url()), "<h2>소제목</h2>", html=False)
        self.client.post(reverse("naver_writing:delete", args=[post.pk]))
        self.assertFalse(Post.objects.exists())

    def test_bulk_moves_keep_status_and_block_published_rollback(self):
        a = Post.objects.create(title="가")
        b = Post.objects.create(title="나")
        move = reverse("naver_writing:move")
        self.client.post(move, {"pk": a.pk, "to": "post"})
        a.refresh_from_db()
        self.assertEqual(a.stage, "temp")
        self.client.post(move, {"ids": [a.pk, b.pk], "to": "review"})
        self.assertEqual(Post.objects.filter(stage="review").count(), 2)
        self.client.post(reverse("naver_writing:status", args=[a.pk]), {"field": "review_status", "value": "done"})
        self.client.post(move, {"pk": a.pk, "to": "post"})
        self.client.post(reverse("naver_writing:status", args=[a.pk]), {"field": "publish_status", "value": "done"})
        self.client.post(move, {"pk": a.pk, "to": "review"})
        a.refresh_from_db()
        self.assertEqual((a.stage, a.review_status, a.publish_status), ("post", "done", "done"))
        self.assertIsNotNone(a.published_on)

    def test_status_cannot_change_arbitrary_fields(self):
        post = Post.objects.create(title="원고")
        for field, value in [("stage", "post"), ("title", "바꾸기"), ("review_status", "invalid")]:
            self.client.post(reverse("naver_writing:status", args=[post.pk]), {"field": field, "value": value})
        post.refresh_from_db()
        self.assertEqual((post.title, post.stage, post.review_status), ("원고", "temp", "todo"))

    def test_same_pk_does_not_access_or_mutate_tistory_post(self):
        original = TistoryPost.objects.create(pk=99, title="티스토리 원고")
        for name in ["detail", "edit", "delete"]:
            self.assertEqual(self.client.get(reverse(f"naver_writing:{name}", args=[99])).status_code, 404)
        self.client.post(reverse("naver_writing:move"), {"pk": 99, "to": "review"})
        original.refresh_from_db()
        self.assertEqual(original.stage, "temp")

    def test_neighbors_and_editor_routes(self):
        older = Post.objects.create(title="이전")
        newer = Post.objects.create(title="다음")
        response = self.client.get(newer.get_absolute_url())
        self.assertEqual(response.context["below"], older)
        for url in [reverse("naver_writing:create"), reverse("naver_writing:edit", args=[newer.pk])]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "naver-editor.js")
            self.assertContains(response, 'aria-label="줄간격"')
            self.assertContains(response, 'id="nv-preview"')
            self.assertNotContains(response, 'data-ed-mode="html"')

    @override_settings(REQUIRE_LOGIN=True, MIDDLEWARE=[
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.auth.middleware.LoginRequiredMiddleware",
    ])
    def test_new_routes_require_server_login(self):
        self.client.logout()
        for name in ["list", "review", "posts", "create", "convert"]:
            self.assertEqual(self.client.get(reverse(f"naver_writing:{name}")).status_code, 302)

    def test_converter_rejects_get_and_cleans_paste(self):
        url = reverse("naver_writing:convert")
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url, {"kind": "markdown", "content": "## 소제목\n\n[사진] 내 사진\n\n|이름|값|\n|---|---|\n|가|나|"})
        out = response.json()["html"]
        self.assertIn("<h2>소제목</h2>", out)
        self.assertIn('class="wr-slot"', out)
        self.assertIn("<table", out)


class NaverFormattingTests(TestCase):
    def test_edited_typography_survives_repeated_save_and_render(self):
        body = '<p style="line-height:200%;text-align:center"><span style="font-family:Nanum Myeongjo;font-size:24px;color:#123456;background-color:#fff3b0"><strong>강조</strong></span><sup>2</sup><sub>1</sub></p>'
        first = clean_html(body)
        self.assertEqual(first, clean_html(render_body(first)))
        for value in ["line-height:200%", "text-align:center", "font-family:Nanum Myeongjo", "font-size:24px", "color:#123456", "background-color:#fff3b0", "<sup>2</sup>", "<sub>1</sub>"]:
            self.assertIn(value, first)

    def test_all_quote_and_divider_styles_survive(self):
        for style in QUOTE_STYLES:
            self.assertIn(style, render_body(f'<blockquote style="{style}"><p>인용</p></blockquote>'))
        for style in HR_STYLES:
            self.assertIn(style, render_body(f'<hr style="{style}">'))

    def test_pasted_scripts_and_unsafe_css_and_links_are_removed(self):
        out = clean_html('<p onclick="x()" style="color:#123456;position:fixed;background:url(https://bad);font-size:999px">본문<script>alert(1)</script><span style="font-family:evil;color:expression(x)">텍스트</span><a href="javascript:alert(1)">링크</a><img src="data:image/svg+xml;base64,aaaa"><iframe src="https://bad"></iframe></p>')
        for forbidden in ["onclick", "script", "alert", "position", "url(", "999px", "expression", "svg", "iframe", "evil"]:
            self.assertNotIn(forbidden, out)
        self.assertIn("color:#123456", out)
        self.assertIn("텍스트", out)

    def test_raster_photo_is_kept_but_svg_is_not(self):
        out = clean_html('<p><img src="data:image/jpeg;base64,/9j/AA==" alt="사진"></p>')
        self.assertIn("data:image/jpeg;base64,/9j/AA==", out)
        self.assertNotIn("<img", clean_html('<p><img src="data:image/svg+xml;base64,AAAA"></p>'))

    def test_plain_excerpt_and_count_drop_photo_slots(self):
        post = Post(body="## 소제목\n\n본문\n\n[사진] 사진 설명")
        self.assertEqual(post.excerpt, "소제목 본문")
        self.assertEqual(plain_text(render_body(post.body), drop_slots=True), "소제목\n본문")

    def test_form_rejects_oversized_body(self):
        form = PostForm({"title": "사진 원고", "body": "가" * 700000})
        self.assertFalse(form.is_valid())
        self.assertIn("body", form.errors)

    def test_clipboard_html_inlines_sizes_and_naver_font_names(self):
        out = paste_html('<h2>제목</h2><p style="text-align:center"><strong style="font-family:&quot;Nanum Myeongjo&quot;;font-size:24px">강조</strong></p>')
        self.assertIn('font-size:24px', out)
        self.assertIn('font-family:나눔명조', out)
        self.assertIn('font-family:나눔고딕', out)
        self.assertIn('text-align:center', out)
        # 사이트 변환본은 원문 화면과 가까운 나눔바른고딕 16px (2026-10-21 사용자). 빈 줄도 같은 글꼴, 표 칸은 15px
        from .render import CONVERT_FONT
        out = paste_html("<p>가</p><table><tr><td>칸</td></tr></table>", gaps=True, font=CONVERT_FONT)
        self.assertIn('<p style="font-family:나눔바른고딕;font-size:16px;line-height:1.8;margin:0">가</p>', out)
        self.assertIn('<p style="font-family:나눔바른고딕;font-size:16px;line-height:1.8;margin:0">&nbsp;</p>', out)
        self.assertIn('font-family:나눔바른고딕;font-size:15px', out)
        self.assertNotIn("나눔고딕", out)
        # 글 덩어리(## 소제목) 앞은 빈 줄 셋 (2026-10-22 사용자: 덩어리 사이가 답답하다)
        out = paste_html("<p>가</p><h2>소제목</h2><p>나</p>", gaps=True)
        self.assertEqual(out.split("<h2")[0].count("&nbsp;"), 3)
        self.assertEqual(out.split("<h2")[1].count("&nbsp;"), 1)

    def test_work_title_vertical_bar(self):
        """영화·OTT: '::: 작품' 카드가 있는 소제목은 왼쪽 회색 막대 + 작품 이름 + 아래 작은 공개일 (2026-10-23 사용자).
        인용으로 그리면 네이버가 '따옴표' 인용구로 바꿔서 표(왼쪽 칸 바탕색이 막대)로 그린다."""
        from .render import WORK_BAR, WORK_CELL, WORK_TABLE
        body = ("> 요약.\n\n## 한눈에 보기\n\n| 공개일 | 작품 |\n|---|---|\n| 11월 6일 | 가능한 사랑 |\n\n"
                "## 데블스 플랜: 데드 어게인 · 11월 10일\n\n두뇌 서바이벌이에요.\n\n::: 작품 | 데블스 플랜\n📅 공개 | 11월 10일\n:::\n")
        out = render_body(body)
        self.assertIn("<h2>한눈에 보기</h2>", out)  # 카드 없는 소제목은 그대로
        self.assertIn(f'<table style="{WORK_TABLE}"><tbody><tr><td style="{WORK_BAR}">\xa0</td><td style="{WORK_CELL}">'
                      '<p style="font-size:19px;color:#555555">데블스 플랜: 데드 어게인</p>'
                      '<p style="font-size:13px;color:#888888">11월 10일</p></td></tr></tbody></table>', out)
        self.assertNotIn("<h2>데블스", out)
        self.assertNotIn("<blockquote", out.split("한눈에 보기")[1])  # 네이버가 따옴표 인용구로 바꾸지 않게
        pasted = paste_html(out, gaps=True)
        self.assertIn("background-color:#555555", pasted)
        before = pasted.split("데블스 플랜: 데드")[0]
        self.assertEqual(before[before.rindex("</table>", 0, before.rindex("<table")):].count("&nbsp;"), 3)  # 글 덩어리처럼 빈 줄 셋

    def test_first_summary_one_sentence_per_line(self):
        """맨 위 인용 상자(첫 요약)는 문장마다 줄바꿈. 뒤의 인용은 그대로 (2026-10-23 사용자)"""
        out = render_body("> 세 편이에요. 6일 영화, 10일 예능 순서예요! 1.5배 빨라요\n\n본문.\n\n## 소제목\n\n> 가요. 나요.\n")
        self.assertIn("세 편이에요.<br>\n6일 영화, 10일 예능 순서예요!<br>\n1.5배 빨라요", out)
        self.assertIn("가요. 나요.", out)
