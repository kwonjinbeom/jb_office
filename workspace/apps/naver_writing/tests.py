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

    def test_clipboard_blank_line_before_headings(self):
        # 네이버는 margin 을 버려 소제목이 앞 문단에 붙는다 → 소제목 앞에 빈 줄 (맨 앞 소제목은 빼고)
        out = paste_html("<h2>첫 제목</h2><p>본문</p><h2>둘째</h2><p>끝</p>")
        self.assertTrue(out.startswith("<h2"))
        self.assertEqual(out.count("<br></p><h2"), 1)
