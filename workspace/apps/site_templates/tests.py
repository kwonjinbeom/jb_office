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
        self.assertEqual(PlatformFormat.objects.count(), 4)
        self.assertIn("개발자", SiteTemplate.objects.get(blog=self.memorily).tone)
        res = self.client.get(reverse("site_templates:index"))
        self.assertContains(res, "memorily")
        self.assertContains(res, "사이트별 템플릿")  # 메뉴
        self.assertEqual([p.title for p in res.context["posts"]], ["자바 정리"])  # 발행예정글 · 발행 전 · 미변환
        self.assertEqual(res.context["ready_ids"], str(self.pl.pk))  # 넣은 글은 변환 버튼
        self.assertContains(res, f'href="?site={self.java.sel}"')  # 왼쪽 사이트 카테고리 트리

    def test_category_concept_and_convert_button_scope(self):
        from apps.writing.models import Post as T
        unmapped = T.objects.create(title="아직 안 넣은 글", stage="post")
        T.objects.create(title="발행한 글", stage="post", publish_status="done")
        other = SiteCategory.objects.get(blog__name="black_lukey", name="낙서장")
        res = self.client.get(reverse("site_templates:index"), {"site": other.sel})
        posts = {p.title: p for p in res.context["posts"]}
        self.assertEqual(set(posts), {"자바 정리", "아직 안 넣은 글"})
        self.assertEqual(posts["자바 정리"].ready, [])  # 다른 카테고리에 넣은 글은 버튼 없음
        self.assertEqual(res.context["ready_count"], 0)
        self.assertContains(res, "다른 카테고리")
        self.assertContains(res, "매핑 먼저")
        url = reverse("site_templates:index")
        res = self.client.post(f"{url}?site={self.java.sel}", {"k-concept": "자바 기초를 예제 하나로"})
        self.java.refresh_from_db()
        self.assertEqual(self.java.concept, "자바 기초를 예제 하나로")
        res = self.client.get(url, {"site": self.java.sel})
        self.assertEqual(res.context["ready_count"], 1)
        self.assertContains(res, "자바 기초를 예제 하나로")
        self.assertIn("## 카테고리 컨셉\n- Java: 자바 기초를 예제 하나로", prompt.build(self.pl))  # 요청문에 카테고리 컨셉
        self.pl.convert_status = "done"
        self.pl.save()
        res = self.client.get(url)
        self.assertEqual([p.title for p in res.context["posts"]], ["아직 안 넣은 글"])  # 변환한 글은 아래 '변환한 글'로
        self.assertEqual([pl.pk for pl in res.context["done"]], [self.pl.pk])
        self.assertTrue(unmapped)

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

    def test_site_page_saves_template_and_format(self):
        url = reverse("site_templates:site", args=[self.memorily.pk])
        self.client.post(url, {"part": "template", "c-content": "새 컨셉", "t-tone": "새 말투", "t-structure": "", "t-rules": ""})
        self.assertEqual(SiteTemplate.objects.get(blog=self.memorily).tone, "새 말투")
        self.memorily.refresh_from_db()
        self.assertEqual(self.memorily.content, "새 컨셉")  # 컨셉도 여기서 (운영 화면과 같은 값)
        self.client.post(url, {"part": "format", "f-guide": "새 포맷"})
        self.assertEqual(PlatformFormat.objects.get(platform="tistory").guide, "새 포맷")
        res = self.client.get(url)
        self.assertNotContains(res, "자바 정리")  # 상세는 컨셉·템플릿만, 글 변환은 메인에서
        self.assertContains(res, f'href="{reverse("site_templates:index")}?site={self.memorily.sel}"')  # 뒤로 (그 사이트를 고른 채)

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
        self.assertTrue(PlatformFormat.objects.get(platform="naver").guide.startswith("붙이는 곳: 본문에 '서식 그대로'"))
        self.assertIn("HTML 보기", PlatformFormat.objects.get(platform="blogger").guide)

    def test_copy_buttons_follow_platform(self):
        res = self.client.get(reverse("site_templates:convert", args=[self.place("black_lukey", "낙서장").pk]))
        self.assertContains(res, 'data-copy-rich="#st-paste"')  # 네이버: 서식 그대로
        self.assertIn("style=", res.context["paste_html"])  # 네이버는 인라인 style 을 단 서식 HTML
        res = self.client.get(reverse("site_templates:convert", args=[self.place("밤밤").pk]))
        self.assertContains(res, "본문 HTML (HTML 보기)")
        self.assertEqual(res.context["clean_html"], "<h2>소제목</h2>\n<p><strong>굵게</strong> 본문</p>")  # 꾸밈 없는 HTML
        res = self.client.get(reverse("site_templates:convert", args=[self.place("워드프레스").pk]))
        self.assertContains(res, 'data-copy="#st-raw"')  # 워드프레스: 마크다운 그대로
        self.assertContains(res, "태그1, 태그2")
        self.assertIn("## 돌려줄 것", res.context["request_text"])
        self.assertIn("블록 에디터", res.context["request_text"])  # 그 플랫폼 포맷 규칙이 요청문에 들어간다
