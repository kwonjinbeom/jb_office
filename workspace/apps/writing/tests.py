from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Post
from .render import clean_html, is_html, plain_text, render_body

Stage = Post.Stage


class PostPipelineTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)

    def test_three_screens_open(self):
        Post.objects.create(title="임시 글", stage=Stage.TEMP)
        Post.objects.create(title="검토 글", stage=Stage.REVIEW)
        Post.objects.create(title="포스트 글", stage=Stage.POST)
        for name, title, others in [
            ("writing:list", "임시 글", ["검토 글", "포스트 글"]),
            ("writing:review", "검토 글", ["임시 글", "포스트 글"]),
            ("writing:posts", "포스트 글", ["임시 글", "검토 글"]),
        ]:
            res = self.client.get(reverse(name))
            self.assertEqual(res.status_code, 200)
            self.assertContains(res, title)
            for other in others:
                self.assertNotContains(res, other)
        res = self.client.get(reverse("writing:posts"))
        self.assertContains(res, "미작성")
        self.assertContains(res, "미발행")

    def test_create_goes_to_requested_screen(self):
        self.client.post(reverse("writing:create"), {"stage": "temp", "title": "새 글", "summary": "요약"})
        self.assertEqual(Post.objects.get(title="새 글").stage, Stage.TEMP)
        self.client.post(reverse("writing:create"), {"stage": "post", "title": "새 포스트",
                                                     "write_status": "todo", "publish_status": "todo"})
        self.assertEqual(Post.objects.get(title="새 포스트").stage, Stage.POST)

    def test_create_opens_detail(self):
        res = self.client.post(reverse("writing:create"), {"stage": "temp", "title": "새 글", "body": "본문"})
        self.assertRedirects(res, Post.objects.get(title="새 글").get_absolute_url())

    def test_move_one_step_each_way(self):
        post = Post.objects.create(title="글")
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "review"})
        post.refresh_from_db()
        self.assertEqual(post.stage, Stage.REVIEW)
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "post"})
        post.refresh_from_db()
        self.assertEqual(post.stage, Stage.POST)
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "review"})
        post.refresh_from_db()
        self.assertEqual(post.stage, Stage.REVIEW)

    def test_temp_jumps_to_post_but_not_back(self):
        """임시글 → 발행예정글은 검토 없이 바로 (2026-10-27 사용자). 거꾸로는 한 칸씩"""
        post = Post.objects.create(title="글")
        res = self.client.get(post.get_absolute_url())
        self.assertContains(res, 'name="to" value="post"')
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "post"})
        post.refresh_from_db()
        self.assertEqual(post.stage, Stage.POST)
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "temp"})
        post.refresh_from_db()
        self.assertEqual(post.stage, Stage.POST)

    def test_bulk_move(self):
        a = Post.objects.create(title="가")
        b = Post.objects.create(title="나")
        self.client.post(reverse("writing:move"), {"ids": [a.pk, b.pk], "to": "review"})
        self.assertEqual(Post.objects.filter(stage=Stage.REVIEW).count(), 2)

    def test_published_post_stays(self):
        post = Post.objects.create(title="글", stage=Stage.POST, publish_status=Post.Publish.DONE)
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "review"})
        post.refresh_from_db()
        self.assertEqual(post.stage, Stage.POST)

    def test_status_keeps_when_moving(self):
        post = Post.objects.create(title="글", stage=Stage.REVIEW)
        self.client.post(reverse("writing:status", args=[post.pk]), {"field": "review_status", "value": "done"})
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "post"})
        self.client.post(reverse("writing:move"), {"pk": post.pk, "to": "review"})
        post.refresh_from_db()
        self.assertEqual(post.review_status, Post.Review.DONE)

    def test_publish_done_sets_date(self):
        post = Post.objects.create(title="글", stage=Stage.POST)
        self.client.post(reverse("writing:status", args=[post.pk]), {"field": "publish_status", "value": "done"})
        post.refresh_from_db()
        self.assertTrue(post.is_published)
        self.assertIsNotNone(post.published_on)

    def test_invalid_status_rejected(self):
        post = Post.objects.create(title="글", stage=Stage.POST)
        self.client.post(reverse("writing:status", args=[post.pk]), {"field": "publish_status", "value": "doing"})
        self.client.post(reverse("writing:status", args=[post.pk]), {"field": "stage", "value": "temp"})
        post.refresh_from_db()
        self.assertEqual(post.publish_status, Post.Publish.TODO)
        self.assertEqual(post.stage, Stage.POST)

    def test_edit_and_delete(self):
        post = Post.objects.create(title="글", stage=Stage.REVIEW)
        res = self.client.post(reverse("writing:edit", args=[post.pk]),
                               {"title": "고친 글", "summary": "", "body": "본문", "tags": "가, 나",
                                "review_status": "doing"})
        self.assertRedirects(res, reverse("writing:detail", args=[post.pk]))
        post.refresh_from_db()
        self.assertEqual((post.title, post.review_status, post.tags), ("고친 글", Post.Review.DOING, "가, 나"))
        self.client.post(reverse("writing:delete", args=[post.pk]))
        self.assertFalse(Post.objects.exists())

    def test_detail_reads_like_a_blog_post(self):
        body = (
            "첫 문단\n\n## 소제목\n\n[사진] 단풍 사진\n[그림] 그림1.png\n[캡션] 남쪽으로 내려와요\n\n"
            "| 산 | 날짜 |\n|---|---|\n| 설악산 | 10/20 |"
        )
        post = Post.objects.create(title="단풍 절정", body=body, tags="#단풍절정, 가을여행", stage=Stage.REVIEW)
        res = self.client.get(reverse("writing:detail", args=[post.pk]))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "<h2>소제목</h2>")
        self.assertContains(res, "#단풍절정")
        self.assertContains(res, "#가을여행")
        self.assertContains(res, "점선 상자 2곳")
        self.assertNotContains(res, "복사해서 붙여넣기")  # 글 보기는 본문을 넓게 (복사 줄 없음)
        self.assertContains(res, 'data-paper-width="mobile"')  # PC·모바일은 단계 탭 줄에
        self.assertContains(res, 'action="/blog/posts/site/"')  # 검토글은 사이트를 고른다 (검토 상태 대신)
        self.assertContains(res, "사이트 고르기")

    def test_detail_neighbors_follow_list_order(self):
        older = Post.objects.create(title="먼저 쓴 글")
        newer = Post.objects.create(title="나중 쓴 글")
        res = self.client.get(reverse("writing:detail", args=[newer.pk]))
        self.assertEqual(res.context["below"], older)
        self.assertIsNone(res.context["above"])

    def test_list_rows_open_detail(self):
        post = Post.objects.create(title="글")
        res = self.client.get(reverse("writing:list"))
        self.assertContains(res, reverse("writing:detail", args=[post.pk]))


class RenderTests(TestCase):
    def test_paste_html_has_inline_styles(self):
        out = render_body("| a | b |\n|---|:-:|\n| 1 | 2 |\n\n> 인용\n\n---")
        self.assertIn('<table style="border-collapse:collapse', out)
        self.assertIn("text-align:center", out)  # 가운데 정렬 칸
        self.assertIn('<blockquote data-ke-style="style2" style="', out)
        self.assertIn('<hr style="', out)

    def test_bold_before_korean_particle(self):
        # 문장부호로 끝나는 굵게 + 바로 붙은 조사: 마크다운 변환기만으로는 ** 가 글자로 남는다
        out = render_body('그건 **"따옴표"**다. **10%**를 넘고 **(괄호)**도. `**코드**`')
        self.assertIn('<strong>"따옴표"</strong>다', out)
        self.assertIn("<strong>10%</strong>를", out)
        self.assertIn("<strong>(괄호)</strong>도", out)
        self.assertIn("<code>**코드**</code>", out)

    def test_bracket_colon_slot(self):
        # 변환 요청문은 [사진: 설명] 꼴로 돌려받는다 → 사진 자리 상자
        out = render_body("[사진: 세일 달력]\n\n[그림: 그림1.png]")
        self.assertIn('class="wr-slot"', out)
        self.assertIn("📷 세일 달력", out)
        self.assertIn("<strong>그림1.png</strong>", out)
        self.assertNotIn("[사진", out)

    def test_slots_and_captions(self):
        out = render_body("📷 사진 1: 직접 찍은 사진\n[그림] 그림1.png\n[캡션] 설명 <b>")
        self.assertIn("📷 사진 1: 직접 찍은 사진", out)
        self.assertIn("<strong>그림1.png</strong>", out)
        self.assertIn("설명 &lt;b&gt;", out)  # 표시 줄의 글은 이스케이프한다
        self.assertEqual(out.count('class="wr-slot"'), 2)

    def test_single_newline_is_line_break(self):
        self.assertIn("<br", render_body("한 줄\n다음 줄"))

    def test_image_with_italic_caption(self):
        out = render_body("![단풍 사진](https://example.com/a.jpg)\n\n*북쪽에서 내려와요.*")
        self.assertIn('style="max-width:100%;height:auto"', out)
        self.assertIn("margin-top:-8px\">북쪽에서 내려와요.</p>", out)
        self.assertNotIn("<em>", out)

    def test_local_image_file_becomes_figure_slot(self):
        out = render_body("![시기표](그림1_단풍.png)\n*캡션*")
        self.assertIn('class="wr-slot"', out)
        self.assertIn("<strong>그림1_단풍.png</strong>", out)
        self.assertNotIn("<img", out)
        self.assertIn(">캡션</p>", out)

    def test_char_count_skips_slots_and_comments(self):
        out = render_body("가나다\n\n[사진] 아주 긴 사진 설명\n\n<!-- 메모 -->")
        self.assertEqual(plain_text(out, drop_slots=True), "가나다")

    def test_tag_list(self):
        self.assertEqual(Post(tags="#가, 나\n다,, ").tag_list, ["가", "나", "다"])

    def test_clean_html_keeps_blog_markup_only(self):
        out = clean_html(
            '<p>가<b>굵게</b><span style="color:red">빨강</span></p><script>alert(1)</script>'
            '<h1>큰제목</h1><p onclick="x()" style="text-align: center;">가운데</p>'
            '<p class="wr-slot" style="border:1px dashed #fca5a5">📷 사진</p><p class="evil">x</p>'
            '<a href="javascript:alert(1)">나쁜</a><img src="javascript:x"><img src="https://i.com/a.jpg" alt="a">'
            '<p style="background:url(http://x)">배경</p><div>디브</div>'
        )
        self.assertNotIn("script", out)
        self.assertNotIn("alert", out)
        self.assertNotIn("onclick", out)
        self.assertNotIn("span", out)
        self.assertNotIn("url(", out)
        self.assertNotIn('class="evil"', out)
        self.assertIn("<strong>굵게</strong>", out)
        self.assertIn("<h2>큰제목</h2>", out)
        self.assertIn('<p style="text-align: center;">가운데</p>', out)
        self.assertIn('<p class="wr-slot"', out)
        self.assertIn('<img src="https://i.com/a.jpg" alt="a">', out)
        self.assertIn("<p>디브</p>", out)
        self.assertEqual(out.count("<img"), 1)

    def test_editor_html_gets_paste_styles(self):
        self.assertTrue(is_html("<p>가</p>"))
        self.assertFalse(is_html("## 소제목"))
        out = render_body("<p>가</p><table><tbody><tr><td>칸</td></tr></tbody></table><blockquote><p>인용</p></blockquote><hr>")
        self.assertIn('<table style="border-collapse:collapse', out)
        self.assertIn('<td style="border:1px solid', out)
        self.assertIn('<blockquote data-ke-style="style2" style="', out)
        self.assertIn('<hr style="', out)

    def test_table_header_survives_tistory_paste(self):
        # 티스토리 기본 모드는 <thead>/<th> 줄을 표 밖으로 빼므로, 머리글도 굵은 보통 칸으로 만든다
        out = render_body("| 산 | 날짜 |\n|---|---|\n| 설악산 | 10/20 |")
        self.assertNotIn("<th", out)
        self.assertNotIn("<thead", out)
        self.assertIn("<strong>산</strong></td>", out)
        self.assertIn("background:#f3f4f6", out)

    def test_hot_row_gets_color(self):
        """첫 칸이 🔥 인 표 줄은 칸마다 연한 주황 바탕 (공모주 화제 종목, 2026-10-22 사용자). 편집기 HTML 로 다시 걸러도 남는다."""
        out = render_body("| 종목 | 공모가 |\n|---|---|\n| 🔥 큰회사 | 30,000 |\n| 작은회사 | 9,000 |")
        hot, plain = out.split("큰회사")[0], out.split("큰회사")[1]
        self.assertEqual(hot.count("background:#fff4e5"), 1)
        self.assertEqual(plain.count("background:#fff4e5"), 1)  # 같은 줄의 둘째 칸까지, 다음 줄은 칠하지 않는다
        self.assertNotIn("#fff4e5", plain.split("</tr>", 1)[1])
        self.assertEqual(render_body(out), out)

    def test_markdown_raw_html_is_cleaned_too(self):
        out = render_body('본문 <a href="javascript:alert(1)">링크</a> <img src=x onerror="alert(1)">')
        self.assertNotIn("javascript", out)
        self.assertNotIn("onerror", out)


    def test_quote_box_uses_body_font_on_tistory(self):
        """인용 상자 (맨 위 결론): 티스토리 기본 인용(가운데 · 명조) 대신 세로줄 인용 + 본문 글꼴·왼쪽 정렬 (2026-10-21 사용자)"""
        out = render_body("> 11월 1일 구매분부터 세금까지 다 내고\n\n본문")
        self.assertIn('<blockquote data-ke-style="style2" style="', out)
        self.assertIn("font-family:inherit", out)
        self.assertIn('<p style="font-family:inherit;font-size:inherit;line-height:inherit;font-style:normal;text-align:left">11월', out)
        self.assertEqual(render_body(out), out)  # 다시 그려도 같다 (편집기에 저장한 HTML)
        self.assertIn("<p>본문</p>", out)  # 인용 밖 문단은 그대로


class EditorTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)

    def test_editor_opens_markdown_body_as_blog_html(self):
        post = Post.objects.create(title="글", body="## 소제목\n\n**굵게**")
        res = self.client.get(reverse("writing:edit", args=[post.pk]))
        self.assertContains(res, 'id="wr-editor"')
        self.assertContains(res, "<h2>소제목</h2>", html=False)
        self.assertContains(res, "<strong>굵게</strong>", html=False)

    def test_save_from_editor_keeps_clean_html(self):
        post = Post.objects.create(title="글")
        self.client.post(reverse("writing:edit", args=[post.pk]), {
            "title": "줄\n바뀐   제목", "summary": "", "tags": "",
            "body": '<p>본문<script>x</script></p><h2>소제목</h2><div>디브</div>',
        })
        post.refresh_from_db()
        self.assertEqual(post.title, "줄 바뀐 제목")
        self.assertEqual(post.body, "<p>본문</p><h2>소제목</h2><p>디브</p>")

    def test_convert_endpoint(self):
        url = reverse("writing:convert")
        md = self.client.post(url, {"kind": "markdown", "content": "## 소제목\n\n[사진] 단풍"}).json()["html"]
        self.assertIn("<h2>소제목</h2>", md)
        self.assertIn('class="wr-slot"', md)
        web = self.client.post(url, {"kind": "html", "content": '<div style="font-family:x"><b>굵게</b> 글</div>'}).json()["html"]
        self.assertIn("<strong>굵게</strong>", web)
        self.assertNotIn("font-family", web)
        text = self.client.post(url, {"kind": "text", "content": "첫 줄\n둘째 줄\n\n새 문단 <b>"}).json()["html"]
        self.assertEqual(text, "<p>첫 줄<br>둘째 줄</p><p>새 문단 &lt;b&gt;</p>")
        self.assertEqual(self.client.get(url).status_code, 405)


DRAFT_MD = """# [원고] T99 · 시험

| 항목 | 내용 |
|---|---|
| 형식 | 시험 |

---

<!-- 본문 시작 -->

# 시험 원고 제목

> 제목 대안: 다른 제목

첫 문단이에요.

## 소제목

[사진] 사진 자리

<!-- 본문 끝 -->

---

태그: 가, 나, 다

소개: 시험 원고 소개 한 줄.
"""


class DraftImportTests(TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path

        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "T99_시험").mkdir()
        (root / "T99_시험" / "원고.md").write_text(DRAFT_MD, encoding="utf-8")
        (root / "T98_본문없음").mkdir()
        (root / "T98_본문없음" / "원고.md").write_text("# 메모만 있는 파일\n", encoding="utf-8")
        self.settings_ctx = self.settings(WRITING_DRAFTS_DIR=root)
        self.settings_ctx.enable()

    def tearDown(self):
        self.settings_ctx.disable()
        self.tmp.cleanup()

    def test_parse_takes_body_tags_summary(self):
        from .drafts import parse

        d = parse(DRAFT_MD, "T99_시험")
        self.assertEqual(d.title, "시험 원고 제목")
        self.assertTrue(d.body.startswith("첫 문단이에요."))
        self.assertNotIn("제목 대안", d.body)
        self.assertNotIn("본문 끝", d.body)
        self.assertEqual((d.tags, d.summary, d.code), ("가, 나, 다", "시험 원고 소개 한 줄.", "T99"))
        self.assertIsNone(parse("# 메모만\n"))
        # 본문에 제목 줄이 없으면 맨 위 '# [원고] T번호 · 제목' 에서 (T61·T62)
        d = parse("# [원고] T61 · iOS 27 업데이트 해도 되나?\n\n제작 정보\n<!-- 본문 시작 -->\n\n**결론부터** 올려도 됩니다.\n<!-- 본문 끝 -->\n")
        self.assertEqual((d.title, d.body), ("iOS 27 업데이트 해도 되나?", "**결론부터** 올려도 됩니다."))
        self.assertIsNone(parse("제작 정보\n<!-- 본문 시작 -->\n제목 없는 본문\n<!-- 본문 끝 -->\n"))

    def test_import_page_lists_only_real_drafts(self):
        res = self.client.get(reverse("writing:import"))
        self.assertContains(res, "시험 원고 제목")
        self.assertNotContains(res, "메모만 있는 파일")
        self.assertContains(res, "새 원고")

    def test_target_comes_from_site_line(self):
        """원고의 `사이트:` 줄이 타겟이 된다. 타겟 칸 전에 들어온 같은 제목 글은 비어 있던 타겟만 채운다."""
        from pathlib import Path

        from .forms import PostForm
        from .views import auto_import_drafts

        root = Path(self.tmp.name)
        md = DRAFT_MD.replace("| 항목 | 내용 |", "사이트: memorily\n\n| 항목 | 내용 |", 1)
        (root / "T97_타겟").mkdir()
        (root / "T97_타겟" / "원고.md").write_text(md.replace("# 시험 원고 제목", "# 타겟 원고 제목"), encoding="utf-8")
        (root / "T96_새글").mkdir()
        (root / "T96_새글" / "원고.md").write_text(md.replace("# 시험 원고 제목", "# 새 타겟 원고"), encoding="utf-8")
        old = Post.objects.create(title="타겟 원고 제목")  # 타겟 칸이 생기기 전에 가져온 글
        auto_import_drafts()
        old.refresh_from_db()
        self.assertEqual(old.target, "memorily")
        self.assertEqual(Post.objects.filter(title="타겟 원고 제목").count(), 1)
        self.assertEqual(Post.objects.get(title="새 타겟 원고").target, "memorily")
        self.assertEqual(Post.objects.get(title="시험 원고 제목").target, "")  # 사이트 줄이 없는 원고
        res = self.client.get(reverse("posts:view"), {"stage": "temp"})
        self.assertContains(res, "memorily")  # 글 관리 왼쪽 목록에 사이트
        form = PostForm(instance=old)
        self.assertIn(("memorily", "memorily"), form.fields["target"].choices)  # 운영 목록에 없어도 지금 값은 남긴다

    def test_custom_line_marks_custom_post(self):
        """`고정주제:`·`커스텀:` 줄이 있는 원고는 커스텀 글. 그 표시 전에 들어온 같은 제목 글도 커스텀으로 (2026-10-22 사용자)."""
        from pathlib import Path

        from .drafts import parse
        from .views import auto_import_drafts

        root = Path(self.tmp.name)
        for key, line, title in [("T95_고정", "고정주제: 공모주 일정 · 국내", "고정 주제 글"), ("T94_요청", "커스텀: 직접 요청", "요청 글")]:
            (root / key).mkdir()
            md = DRAFT_MD.replace("| 항목 | 내용 |", f"사이트: 눈잎\n{line}\n\n| 항목 | 내용 |", 1).replace("# 시험 원고 제목", f"# {title}")
            (root / key / "원고.md").write_text(md, encoding="utf-8")
            self.assertTrue(parse(md).custom)
        self.assertFalse(parse(DRAFT_MD).custom)
        Post.objects.create(title="요청 글")  # 커스텀 표시 전에 가져온 글
        auto_import_drafts()
        self.assertEqual(set(Post.objects.filter(custom=True).values_list("title", flat=True)), {"고정 주제 글", "요청 글"})
        self.assertFalse(Post.objects.get(title="시험 원고 제목").custom)

    def test_import_creates_temp_post_once(self):
        url = reverse("writing:import")
        res = self.client.post(url, {"keys": ["T99_시험"]})
        self.assertRedirects(res, reverse("writing:list"))
        post = Post.objects.get(title="시험 원고 제목")
        self.assertEqual((post.stage, post.tags, post.summary), (Stage.TEMP, "가, 나, 다", "시험 원고 소개 한 줄."))
        self.assertIn("<h2>소제목</h2>", render_body(post.body))
        self.client.post(url, {"keys": ["T99_시험"]})  # 두 번 가져와도 한 편
        self.assertEqual(Post.objects.filter(title="시험 원고 제목").count(), 1)
        self.assertContains(self.client.get(url), "이미 있음")


class DraftSyncTests(TestCase):
    """원고 폴더 ↔ 글 (2026-10-26 사용자): 같은 원고를 고치면(허브) 글도 고치고, 발행한 글이면 '수정됨' 불."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "T150_허브").mkdir()
        self.write("이번 주 청약·공모주 달력 (10월 27일~11월 9일)", "첫 주 내용")
        self.settings_ctx = self.settings(WRITING_DRAFTS_DIR=self.root)
        self.settings_ctx.enable()

    def tearDown(self):
        self.settings_ctx.disable()
        self.tmp.cleanup()

    def write(self, title, line):
        md = DRAFT_MD.replace("# 시험 원고 제목", f"# {title}").replace("첫 문단이에요.", line)
        (self.root / "T150_허브" / "원고.md").write_text(md, encoding="utf-8")

    def test_hub_edit_updates_post_and_lights_published_lamp(self):
        from apps.blog_types.models import Placement, SiteCategory

        from .views import auto_import_drafts
        auto_import_drafts()
        post = Post.objects.get(source="T150_허브")
        pl = Placement.objects.create(site_category=SiteCategory.objects.filter(blog__name="눈잎").first(), tistory_post=post,
                                      status=Placement.Status.PUBLISHED)
        self.write("이번 주 청약·공모주 달력 (11월 3일~11월 16일)", "둘째 주 내용")
        self.assertEqual(auto_import_drafts(), 0)  # 제목이 바뀌어도 새 글로 생기지 않는다
        post.refresh_from_db(), pl.refresh_from_db()
        self.assertEqual(Post.objects.filter(source="T150_허브").count(), 1)
        self.assertIn("둘째 주 내용", post.body)
        self.assertTrue(post.title.startswith("이번 주 청약·공모주 달력 (11월 3일"))
        self.assertIsNotNone(pl.changed_at)
        self.assertTrue(pl.changed_note.startswith("제목·본문 · 이번 주 청약·공모주 달력 (10월 27일"))

    def test_published_list_and_post_page_pick_up_hub_edit(self):
        """게시글 관리·변환글 보기를 열어도 고친 허브 원고가 반영된다 (2026-10-27 사용자: 글 관리 목록을 안 열면 옛 제목 그대로였다)."""
        from django.contrib.auth import get_user_model

        from apps.blog_types.models import Placement, SiteCategory

        from .views import auto_import_drafts
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        auto_import_drafts()
        post = Post.objects.get(source="T150_허브")
        pl = Placement.objects.create(site_category=SiteCategory.objects.filter(blog__name="눈잎").first(), tistory_post=post,
                                      status=Placement.Status.PUBLISHED)
        for n, url in enumerate([reverse("posts:published"), f"{reverse('site_templates:post')}?p=tistory:{post.pk}"]):
            self.write(f"국내 공모주 일정 ({n + 1}판)", f"{n + 1}판 내용")
            self.assertEqual(self.client.get(url).status_code, 200)
            post.refresh_from_db(), pl.refresh_from_db()
            self.assertEqual(post.title, f"국내 공모주 일정 ({n + 1}판)")
            self.assertIn(f"→ 국내 공모주 일정 ({n + 1}판)", pl.changed_note)

    def test_user_edited_post_is_not_overwritten(self):
        from .views import auto_import_drafts
        auto_import_drafts()
        post = Post.objects.get(source="T150_허브")
        post.body = "사용자가 손질한 본문"
        post.save()
        self.write("이번 주 청약·공모주 달력 (10월 27일~11월 9일)", "고친 원고")
        auto_import_drafts()
        post.refresh_from_db()
        self.assertEqual(post.body, "사용자가 손질한 본문")

    def test_old_post_gets_source_by_title(self):
        from .views import auto_import_drafts
        old = Post.objects.create(title="이번 주 청약·공모주 달력 (10월 27일~11월 9일)", body="그대로")
        auto_import_drafts()
        old.refresh_from_db()
        self.assertEqual(old.source, "T150_허브")
        self.assertEqual(Post.objects.count(), 1)

    def test_old_title_line_links_renamed_hub(self):
        """이미 있는 글을 허브로 바꾸며 제목을 고쳐도 `옛 제목:` 줄로 같은 글을 고친다 (새 글로 생기지 않는다)."""
        from apps.blog_types.models import Placement, SiteCategory

        from .views import auto_import_drafts
        old = Post.objects.create(title="국내 공모주 일정 (10월 22일~12월 초)", body="옛 본문")
        pl = Placement.objects.create(site_category=SiteCategory.objects.filter(blog__name="눈잎").first(), tistory_post=old,
                                      status=Placement.Status.PUBLISHED)
        md = DRAFT_MD.replace("| 항목 | 내용 |", "옛 제목: 국내 공모주 일정 (10월 22일~12월 초)\n\n| 항목 | 내용 |", 1)
        md = md.replace("# 시험 원고 제목", "# 이번 주 청약·공모주 달력 (10월 27일~11월 9일)")
        (self.root / "T150_허브" / "원고.md").write_text(md, encoding="utf-8")
        auto_import_drafts()
        old.refresh_from_db(), pl.refresh_from_db()
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual((old.source, old.title), ("T150_허브", "이번 주 청약·공모주 달력 (10월 27일~11월 9일)"))
        self.assertTrue(pl.changed_note.startswith("제목·본문 · 국내 공모주 일정"))


class TrashNunipKospiTests(TestCase):
    """writing 0026 (2026-10-26 사용자): 눈잎에 넣었던 코스피 글은 휴지통으로."""

    def test_post_and_placement_trashed(self):
        from importlib import import_module

        from django.apps import apps as django_apps

        from apps.blog_types.models import Placement, SiteCategory
        mig = import_module("apps.writing.migrations.0026_trash_nunip_kospi")
        post = Post.objects.create(title=mig.TITLE)
        pl = Placement.objects.create(site_category=SiteCategory.objects.filter(blog__name="눈잎").first(), tistory_post=post)
        keep = Post.objects.create(title="다른 글")
        mig.forward(django_apps, None)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())
        self.assertFalse(Placement.objects.filter(pk=pl.pk).exists())
        self.assertTrue(Post.objects.filter(pk=keep.pk).exists())


class PlanDayTests(TestCase):
    """글쓰기 날짜 (2026-10-28 사용자: 29일로 미리 쓴 글이 28일 횟수·결과에 들어갔다) — 원고 '발행 예정' 줄 · 그날 기획표."""

    def _draft(self, root, key, cls, extra=""):
        folder = root / "원고" / key
        folder.mkdir(parents=True)
        (folder / "원고.md").write_text(f"# [원고] {key}\n\n분류: {cls}\n\n| 항목 | 내용 |\n|---|---|\n{extra}\n"
                                        "<!-- 본문 시작 -->\n# 제목 " + key + "\n본문\n<!-- 본문 끝 -->\n", encoding="utf-8")

    def test_plan_day_and_written_at(self):
        import tempfile
        from datetime import date, datetime, timezone as tz
        from pathlib import Path
        from apps.writing import drafts
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "주제기획").mkdir()
            (root / "주제기획" / "2026-10-29.md").write_text("## 원고\n\n### T178 · 눈잎 > 주택 공고 · 계산\n- …\n", encoding="utf-8")
            self._draft(root, "T178_유보라", "눈잎 > 주택 공고 > 계산")
            self._draft(root, "T178_블랙클로버", "")  # 같은 T번호의 애니 글 (기획 밖)
            self._draft(root, "T200_미리", "워드프레스 > 산과 캠핑 > 코스", "| 발행 예정 | 2026-10-30 (예약) |")
            with self.settings(WRITING_DRAFTS_DIR=root / "원고"):
                found = {d.key: d for d in drafts.list_drafts()}
                self.assertEqual(drafts.plan_day(found["T178_유보라"]), date(2026, 10, 29))
                self.assertIsNone(drafts.plan_day(found["T178_블랙클로버"]))
                self.assertEqual(drafts.plan_day(found["T200_미리"]), date(2026, 10, 30))  # 발행 예정 줄이 먼저
                at = datetime(2026, 10, 28, 14, 5, tzinfo=tz.utc)  # 한국 28일 23:05 에 씀
                moved = drafts.on_day(at, date(2026, 10, 29))
                self.assertEqual((moved.date().isoformat(), moved.hour, moved.minute), ("2026-10-29", 23, 5))
                self.assertIs(drafts.on_day(at, None), at)

    def test_results_count_on_plan_day(self):
        from datetime import date, datetime
        from zoneinfo import ZoneInfo
        from apps.routines.results import _posts
        p = Post.objects.create(title="계양 유보라", stage="temp", body="b", target="눈잎")
        Post.all_objects.filter(pk=p.pk).update(created_at=datetime(2026, 10, 29, 23, 5, tzinfo=ZoneInfo("Asia/Seoul")))
        self.assertTrue(any("계양 유보라" == t for rows in _posts(date(2026, 10, 29)).values() for t, _ in rows))
        self.assertFalse(_posts(date(2026, 10, 28)))
