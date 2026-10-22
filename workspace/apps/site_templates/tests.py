from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.blog_rules.models import Blog
from apps.blog_types.models import Placement, SiteCategory
from apps.writing.models import Post

from . import prompt
from .models import PlatformFormat, SiteTemplate


class SiteTemplateTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)
        self.memorily = Blog.objects.get(name="memorily")
        self.java = SiteCategory.objects.get(blog=self.memorily, name="Java")
        self.post = Post.objects.create(title="자바 정리", stage="post", body="## 소제목\n본문")
        self.pl = Placement.objects.create(site_category=self.java, tistory_post=self.post)

    def test_seed_and_index(self):
        """사이트별 템플릿 (2026-10-22 사용자): 변환은 글 관리로, 여기는 글쓰기·변환 컨셉과 규칙"""
        self.assertEqual(PlatformFormat.objects.count(), 4)
        self.assertIn("개발자", SiteTemplate.objects.get(blog=self.memorily).tone)
        res = self.client.get(reverse("site_templates:index"))
        self.assertContains(res, "memorily")
        self.assertContains(res, "사이트별 템플릿")  # 메뉴
        self.assertContains(res, f'href="?site={self.java.sel}"')  # 왼쪽 사이트 카테고리 트리
        self.assertNotIn("posts", res.context)  # 변환할 글 표는 없다
        self.assertNotContains(res, "변환 가능 글 전체 변환")
        self.assertContains(res, "카테고리 컨셉 0/")  # 사이트마다 요약
        res = self.client.get(reverse("site_templates:index"), {"site": self.memorily.sel})
        self.assertContains(res, "말투·멘트")  # 사이트를 고르면 컨셉·템플릿 (보기만)
        self.assertContains(res, "붙여넣기 포맷")
        self.assertContains(res, "Java")  # 카테고리 컨셉 목록
        self.assertNotContains(res, 'name="t-tone"')  # 고치는 칸 없음

    def test_category_concept(self):
        """카테고리를 고르면 그 컨셉과 같이 적용되는 것 — 보기만 (2026-10-22 사용자: 고치기는 Claude 에게 따로)"""
        self.java.concept = "자바 기초를 예제 하나로"
        self.java.save()
        url = reverse("site_templates:index")
        res = self.client.get(url, {"site": self.java.sel})
        self.assertContains(res, "자바 기초를 예제 하나로")
        self.assertContains(res, "같이 적용되는 것")
        self.assertContains(res, "개발자")  # 사이트 말투가 같이 보인다
        self.assertNotContains(res, "<textarea")  # 고치는 칸 없음
        self.assertIn("## 카테고리 컨셉\n- Java: 자바 기초를 예제 하나로", prompt.build(self.pl))  # 요청문에 카테고리 컨셉
        res = self.client.get(url, {"site": self.memorily.sel})
        self.assertNotContains(res, "<textarea")
        self.assertContains(res, "개발자")

    def test_reconvert_with_comment(self):
        """재변환 (2026-10-22 사용자): 글 관리에서 체크한 글 하나 + 코멘트. 변환 완료여도 다시, 지난 변환본을 코멘트대로"""
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        self.pl.convert_status, self.pl.converted_title, self.pl.converted_body = "done", "지난 제목", "지난 본문 첫 문단"
        self.pl.save()
        url = reverse("site_templates:reconvert")
        self.assertEqual(self.client.post(url, {"p": f"tistory:{self.post.pk}", "note": ""}).status_code, 400)
        data = self.client.post(url, {"p": f"tistory:{self.post.pk}", "note": "첫 문단을 더 짧게"}).json()
        text = data["prompt"]
        self.assertTrue(text.startswith("# 사이트 변환 (재변환)"))
        self.assertIn("## 재변환 코멘트 (사용자)\n첫 문단을 더 짧게", text)
        self.assertIn("## 지난 변환본 (재변환 코멘트대로 고친다)", text)
        self.assertIn("지난 본문 첫 문단", text)
        self.assertTrue(data["key"].startswith("rc-"))
        self.pl.refresh_from_db()
        self.assertEqual((self.pl.convert_status, self.pl.convert_note), ("requested", ""))  # 코멘트는 이번에만
        from apps.writing.models import Post as T
        lone = T.objects.create(title="안 넣은 글", stage="post")
        self.assertEqual(self.client.post(url, {"p": f"tistory:{lone.pk}", "note": "x"}).status_code, 400)

    def test_run_needs_token_then_launches_and_api_saves(self):
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        run = reverse("site_templates:run")
        res = self.client.post(run, {"ids": str(self.pl.pk)})
        self.assertEqual(res.status_code, 400)  # 보고 토큰이 없으면 시작하지 않는다
        self.pl.refresh_from_db()
        self.assertEqual(self.pl.convert_status, "none")
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok-123")
        data = self.client.post(run, {"ids": f"{self.pl.pk},999"}).json()
        self.assertTrue(data["prompt"].startswith("# 사이트 변환"))
        self.assertTrue(data["key"].startswith("cv-"))
        self.assertIn("token=tok-123", data["prompt"])
        self.assertIn(f"workspace/.routine/convert/{self.pl.pk}.md", data["prompt"])
        self.assertIn("## 원문", data["prompt"])
        self.assertIn("## 사실 점검", data["prompt"])  # 변환 때 숫자·날짜·일정을 출처에서 다시 확인
        self.assertIn(f'check@workspace/.routine/convert/{self.pl.pk}-check.md', data["prompt"])
        self.assertIn("- 고침: 원래 값 → 고친 값", data["prompt"])
        self.pl.refresh_from_db()
        self.assertEqual(self.pl.convert_status, "requested")
        api = reverse("site_templates:api_save", args=[self.pl.pk])
        self.client.logout()
        self.assertEqual(self.client.post(f"{api}?token=bad", {"body": "x"}).status_code, 403)
        res = self.client.post(f"{api}?token=tok-123", {"title": "바꾼 제목", "body": "## 바꾼\r\n본문", "tags": "자바, 기초"})
        self.assertEqual(res.content.decode(), f"ok {self.pl.pk} done")
        self.pl.refresh_from_db()
        self.assertEqual((self.pl.convert_status, self.pl.converted_title, self.pl.converted_body, self.pl.converted_tags),
                         ("done", "바꾼 제목", "## 바꾼\n본문", "자바, 기초"))
        self.assertIsNotNone(self.pl.converted_at)
        # Windows curl: 명령줄의 제목·태그는 cp949, 파일로 보낸 본문은 UTF-8 (2026-10-20 제목·태그가 깨졌다)
        from urllib.parse import quote_plus
        mixed = "&".join([f"title={quote_plus('자바 제목', encoding='cp949')}", f"tags={quote_plus('자바, 기초', encoding='cp949')}",
                          f"body={quote_plus('## 본문 소제목', encoding='utf-8')}"])
        self.client.post(f"{api}?token=tok-123", mixed, content_type="application/x-www-form-urlencoded")
        self.pl.refresh_from_db()
        self.assertEqual((self.pl.converted_title, self.pl.converted_tags, self.pl.converted_body),
                         ("자바 제목", "자바, 기초", "## 본문 소제목"))
        # 사실 점검 기록: 저장하고 변환 화면에 보인다 (출처 주소는 링크, 글은 이스케이프)
        check = "- 고침: 11/27 → 11/28 · 거래소 공지 · https://example.com/a?x=1&y=2\r\n- 미정: 12월 일정 · <아직 발표 없음>"
        self.client.post(f"{api}?token=tok-123", {"title": "t", "body": "b", "tags": "", "check": check})
        self.pl.refresh_from_db()
        self.assertTrue(self.pl.converted_check.startswith("- 고침: 11/27 → 11/28"))
        self.client.force_login(get_user_model().objects.get(username="tester"))
        res = self.client.get(reverse("site_templates:convert", args=[self.pl.pk]))
        self.assertContains(res, "사실 점검")
        self.assertContains(res, '<a href="https://example.com/a?x=1&amp;y=2" target="_blank" rel="noopener">')
        self.assertContains(res, "&lt;아직 발표 없음&gt;")

    def test_api_state_reads_with_token(self):
        """PC claude 가 매핑 번호·지난 변환본·컨셉을 읽는다 (2026-10-23, 발행한 글 고쳐 다시 보내기). 토큰이 있어야 한다"""
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        self.pl.converted_body = "지난 변환본"
        self.pl.save()
        url = reverse("site_templates:api_state")
        self.client.logout()
        self.assertEqual(self.client.get(url, {"token": "bad"}).status_code, 403)
        data = self.client.get(url, {"token": "tok", "site": "memorily"}).json()
        site = data["sites"][0]
        self.assertEqual((len(data["sites"]), site["name"]), (1, "memorily"))
        self.assertIn("개발자", site["template"]["tone"])
        self.assertIn("Java", [c["name"] for c in site["categories"]])
        pl = site["placements"][0]
        self.assertEqual((pl["id"], pl["title"], pl["converted_body"]), (self.pl.pk, "자바 정리", "지난 변환본"))

    def test_old_site_page_redirects(self):
        url = reverse("site_templates:site", args=[self.memorily.pk])
        self.assertRedirects(self.client.get(url), f'{reverse("site_templates:index")}?site={self.memorily.sel}',
                             fetch_redirect_response=False)

    def test_convert_flow(self):
        url = reverse("site_templates:convert", args=[self.pl.pk])
        res = self.client.get(url)
        self.assertContains(res, "자바 정리")
        self.assertIn("개발자 1인칭", res.context["request_text"])  # 요청문에 사이트 템플릿이 들어간다
        self.client.post(url, {"action": "request", "convert_note": "짧게", "converted_title": "", "converted_body": ""})
        self.pl.refresh_from_db()
        self.assertEqual((self.pl.convert_status, self.pl.convert_note), ("requested", "짧게"))
        data = self.client.get(reverse("site_templates:requests")).json()
        self.assertEqual(data["count"], 1)
        self.assertIn("짧게", data["items"][0]["prompt"])
        res = self.client.post(url, {"action": "save", "converted_title": "바꾼 제목", "converted_body": "바꾼 본문",
                                     "convert_note": "짧게"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(res.json(), {"ok": True, "status": "done"})
        self.pl.refresh_from_db()
        self.assertEqual((self.pl.convert_status, self.pl.converted_title), ("done", "바꾼 제목"))
        self.assertIsNotNone(self.pl.converted_at)
        self.client.post(url, {"action": "check", "converted_title": "바꾼 제목", "converted_body": "바꾼 본문", "convert_note": ""})
        self.pl.refresh_from_db()
        self.assertEqual(self.pl.convert_status, "checked")
        self.assertEqual(self.client.get(reverse("site_templates:requests")).json()["count"], 0)


class PasteFormatTests(TestCase):
    """플랫폼별 붙여넣기: 포맷 규칙(조사 결과)과 변환 화면의 복사 방식"""

    def setUp(self):
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)
        self.post = Post.objects.create(title="원문", stage="post", body="본문")

    def place(self, blog_name, cat_name=None):
        blog = Blog.objects.get(name=blog_name)
        cat = SiteCategory.objects.filter(blog=blog, name=cat_name).first() if cat_name else None
        cat = cat or SiteCategory.objects.create(blog=blog, name="시험")
        return Placement.objects.create(site_category=cat, tistory_post=self.post, converted_title="바꾼 제목",
                                        converted_body="## 소제목\n\n**굵게** 본문", converted_tags="태그1, 태그2",
                                        convert_status="done")

    def test_guides_come_from_research(self):
        self.assertTrue(PlatformFormat.objects.get(platform="naver").guide.startswith("서식 그대로 붙인다"))  # 0007 에서 줄였다
        self.assertIn("HTML 보기", PlatformFormat.objects.get(platform="blogger").guide)

    def test_naver_paste_gaps_tags_and_check_date(self):
        """네이버 (2026-10-20 사용자): 문단 사이 빈 줄, 태그는 '#태그 #태그', 출처 줄 확인 날짜는 괄호 안 작은 회색"""
        pl = self.place("black_lukey", "낙서장")
        pl.converted_body = "첫 문단\n\n## 소제목\n\n둘째 문단\n\n참고: [출처](https://a.com) (2026년 10월 20일 확인)"
        pl.converted_tags = "태그1, 태그 2, #태그3"
        pl.save()
        res = self.client.get(reverse("site_templates:convert", args=[pl.pk]))
        rich = res.context["paste_html"]
        self.assertEqual(rich.count("&nbsp;</p>"), 5)  # 블록 네 개 사이에 빈 줄 하나씩, ## 소제목 앞만 셋
        self.assertEqual(res.context["converted_html"], rich)  # 미리보기도 붙여넣을 HTML 그대로
        self.assertIn('<span style="color:#999999;font-size:13px">(10.20 확인)</span>', rich)
        self.assertNotIn("2026년 10월 20일 확인", rich)
        self.assertContains(res, f'<textarea id="st-tags-{pl.pk}" hidden>#태그1 #태그2 #태그3</textarea>', html=False)
        self.assertEqual(res.context["tag_items"], ["태그1", "태그2", "태그3"])  # 하나씩 복사 (태그 칸은 Enter 로 하나씩)
        self.assertContains(res, 'data-copy-text="태그2"')
        self.assertTrue(res.context["tag_bookmarklet"].startswith("javascript:"))
        self.assertNotIn(" ", res.context["tag_bookmarklet"])
        self.assertNotIn("#", res.context["tag_bookmarklet"])  # 주소에 # 이 있으면 뒤가 잘린다
        tistory = self.place("memorily")
        res = self.client.get(reverse("site_templates:convert", args=[tistory.pk]))
        self.assertContains(res, f'<textarea id="st-tags-{tistory.pk}" hidden>태그1, 태그2</textarea>', html=False)  # 티스토리는 쉼표 그대로
        self.assertEqual(res.context["tag_items"], [])
        self.assertNotIn("<p>&nbsp;</p>", res.context["paste_html"])  # 티스토리는 네이버식 빈 줄이 아니라 티스토리식 (data-ke-size)

    def test_naver_fixes_apply_to_html_saved_conversion(self):
        """HTML 로 저장한 변환본(예: 롤드컵 입문)도 빈 줄 · 확인 날짜가 같게. 다시 그려도 두 번 감싸지 않는다."""
        from apps.writing.render import render_body
        pl = self.place("black_lukey", "낙서장")
        pl.converted_body = "<p>LoL 공식 안내 기준, 한국 시간, 10월 15일 확인</p><h2>보는 법</h2><p>골드 차이</p>"
        pl.save()
        rich = self.client.get(reverse("site_templates:convert", args=[pl.pk])).context["paste_html"]
        self.assertEqual(rich.count("&nbsp;</p>"), 4)  # 소제목 앞 셋 + 뒤 하나
        self.assertEqual(rich.count("(10.15 확인)</span>"), 1)
        once = render_body(pl.converted_body)
        self.assertEqual(render_body(once), once)
        editor = self.place("black_lukey", "낙서장")
        editor.converted_body = "<p>가</p><p><br></p><p>나</p>"  # 네이버 편집기 꼴: 빈 줄이 이미 있다
        editor.save()
        rich = self.client.get(reverse("site_templates:convert", args=[editor.pk])).context["paste_html"]
        self.assertNotIn("&nbsp;</p>", rich)

    def test_naver_summary_quote_is_naver_quotation(self):
        """네이버 맨 위 결론 인용은 네이버 '따옴표' 인용구로 (2026-10-21 사용자). 미리보기도 그 모양, 티스토리는 세로줄 인용"""
        pl = self.place("black_lukey", "낙서장")
        pl.converted_body = "> 롤을 몰라도 롤드컵은 즐길 수 있어요.\n\n본문"
        pl.save()
        res = self.client.get(reverse("site_templates:convert", args=[pl.pk]))
        self.assertIn("<blockquote", res.context["paste_html"])
        self.assertContains(res, "st-converted st-naver")
        self.assertContains(res, "따옴표")
        tistory = self.place("memorily")
        tistory.converted_body = pl.converted_body
        tistory.save()
        res = self.client.get(reverse("site_templates:convert", args=[tistory.pk]))
        self.assertIn('data-ke-style="style2"', res.context["paste_html"])

    def test_tistory_paste_gaps_and_photo_width(self):
        """티스토리 (2026-10-22 사용자): 스킨이 문단 간격을 0 으로 둬서 답답하다 → 블록 사이 빈 줄, 사진은 가운데 620"""
        pl = self.place("memorily")
        pl.converted_body = "첫 문단\n\n## 소제목\n\n![사진](https://a.com/x.png)\n\n끝"
        pl.save()
        res = self.client.get(reverse("site_templates:convert", args=[pl.pk]))
        html = res.context["paste_html"]
        self.assertEqual(html.count('<p data-ke-size="size16">&nbsp;</p>'), 4)  # 소제목 앞 셋 · 바로 뒤에는 없이 · 사진 뒤 하나
        self.assertIn("첫 문단</p>\n" + '<p data-ke-size="size16">&nbsp;</p>' * 3 + "<h2>", html)
        self.assertIn('<h2>소제목</h2>\n<p style="text-align:center', html)
        self.assertIn('<p style="text-align:center;margin:18px 0"><img width="620" src="https://a.com/x.png"', html)
        self.assertContains(res, "st-converted st-flat")  # 미리보기도 같은 간격
        pl.converted_body = '<p>가</p><p><br></p><p>나</p>'  # 편집기 HTML 은 빈 줄이 이미 있다
        pl.save()
        self.assertNotIn("&nbsp;", self.client.get(reverse("site_templates:convert", args=[pl.pk])).context["paste_html"])

    def test_copy_buttons_follow_platform(self):
        res = self.client.get(reverse("site_templates:convert", args=[self.place("black_lukey", "낙서장").pk]))
        self.assertContains(res, 'data-copy-rich="#st-paste-')  # 네이버: 서식 그대로 (복사 칸 id 에 매핑 번호)
        self.assertIn("style=", res.context["paste_html"])  # 네이버는 인라인 style 을 단 서식 HTML
        tistory = self.place("memorily")
        tistory.converted_body = "| 항목 | 값 |\n|---|---|\n| 가 | **10%**를 |"
        tistory.save()
        res = self.client.get(reverse("site_templates:convert", args=[tistory.pk]))
        html = res.context["clean_html"]  # 티스토리: 티스토리 글쓰기와 같은 인라인 style HTML
        self.assertIn('<table style="border-collapse:collapse', html)
        self.assertNotIn("<th", html)  # 머리글 줄이 표 밖으로 빠지지 않게 보통 칸
        self.assertIn("<strong>10%</strong>를", html)
        self.assertEqual(res.context["paste_html"], html)
        res = self.client.get(reverse("site_templates:convert", args=[self.place("밤밤").pk]))
        self.assertContains(res, "본문 HTML (HTML 보기)")
        self.assertEqual(res.context["clean_html"],  # 블로거도 티스토리처럼 (소제목 바로 뒤는 빈 줄 없이)
                         '<h2>소제목</h2>\n<p><strong>굵게</strong> 본문</p>')
        res = self.client.get(reverse("site_templates:convert", args=[self.place("워드프레스").pk]))
        self.assertContains(res, 'data-copy="#st-raw-')  # 워드프레스: 마크다운 그대로
        self.assertEqual(res.context["clean_html"], "<h2>소제목</h2>\n<p><strong>굵게</strong> 본문</p>")  # 꾸밈 없는 HTML
        self.assertContains(res, "태그1, 태그2")
        self.assertIn("## 돌려줄 것", res.context["request_text"])
        self.assertIn("블록 에디터", res.context["request_text"])  # 그 플랫폼 포맷 규칙이 요청문에 들어간다

    def test_convert_keeps_original_and_fills_photos(self):
        # 변환은 원문이 기준 + 사진·그림 자리는 채우거나 지운다 (2026-10-21 사용자). 워드프레스는 사진 찾기 없이 자리만 지운다
        tistory = self.place("memorily")
        request_text = self.client.get(reverse("site_templates:convert", args=[tistory.pk])).context["request_text"]
        self.assertIn("## 변환 원칙 (원문이 기준)", request_text)
        self.assertIn("## 사진·그림 (변환이 끝까지 채운다", request_text)
        self.assertIn("원문에 자리가 없어도 글마다 두 가지를 판단한다", request_text)  # 사진 1장 · 가공이미지 (2026-10-22 사용자)
        self.assertIn("맞는 사진이 없으면 그 줄을 지운다", request_text)
        self.assertNotIn("못 찾았으면 [사진: 설명]", request_text)
        self.assertNotIn("## 글 다듬기", request_text)  # 원문을 다시 짜게 만들던 규칙
        naver = self.place("black_lukey", "낙서장")
        naver_text = self.client.get(reverse("site_templates:convert", args=[naver.pk])).context["request_text"]
        self.assertIn("## 사진·그림", naver_text)
        self.assertNotIn("사진 → 한두 줄 설명을 반복", naver_text)  # 원문을 다시 짜게 만들던 구성 (0007 에서 뺐다)
        self.assertNotIn("### 구성", naver_text)  # 빈 칸은 늘어놓지 않는다
        self.assertIn("쇼핑커넥트", naver_text)
        self.assertEqual(PlatformFormat.objects.get(platform="naver").guide.count("\n"), 3)
        wordpress = self.place("워드프레스")
        wp_text = self.client.get(reverse("site_templates:convert", args=[wordpress.pk])).context["request_text"]
        self.assertNotIn("## 사진·그림", wp_text)
        self.assertIn("[사진]·📷·[그림] 자리 줄은 변환본에 남기지 않는다", wp_text)
        # 찾아 넣은 사진 + 출처 캡션 → 붙여넣기 HTML 에 실제 이미지와 캡션
        tistory.converted_body = "글\n\n![병원 대기실](https://images.unsplash.com/photo-1?w=1200&q=80)\n*사진: 홍길동 · Unsplash*"
        tistory.save()
        html = self.client.get(reverse("site_templates:convert", args=[tistory.pk])).context["clean_html"]
        self.assertIn('<img width="620" src="https://images.unsplash.com/photo-1?w=1200&amp;q=80" alt="병원 대기실"', html)
        self.assertIn("사진: 홍길동 · Unsplash</p>", html)


class BloggerLabelTests(TestCase):
    """블로거 라벨은 5개쯤 (2026-10-22 사용자: 태그를 그대로 붙여 라벨이 너무 많아졌다)."""

    def test_prompt_asks_five_labels_and_copy_keeps_five(self):
        from .views import _tags_for
        bambam = Blog.objects.get(name="밤밤")
        cat = SiteCategory.objects.create(blog=bambam, name="코스피")
        pl = Placement.objects.create(site_category=cat, tistory_post=Post.objects.create(title="코스피 글", body="본문"),
                                      converted_tags="코스피, 증시, 반도체, 외국인, 환율, 금리, 나스닥, 2026")
        text = prompt.build(pl)
        self.assertIn("## 블로거 라벨", text)
        self.assertIn("첫째는 넣을 카테고리 이름", text)
        self.assertEqual(_tags_for(pl), "코스피, 증시, 반도체, 외국인, 환율")
        pl.site_category = SiteCategory.objects.get(blog__name="눈잎", name="공모주")
        self.assertNotIn("## 블로거 라벨", prompt.build(pl))
