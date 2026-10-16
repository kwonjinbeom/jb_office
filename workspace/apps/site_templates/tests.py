from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.blog_rules.models import Blog
from apps.blog_types.models import Placement, SiteCategory
from apps.writing.models import Post

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
        self.assertContains(res, "미변환 1")
        self.assertContains(res, "사이트별 템플릿")  # 메뉴

    def test_site_page_saves_template_and_format(self):
        url = reverse("site_templates:site", args=[self.memorily.pk])
        self.client.post(url, {"part": "template", "t-tone": "새 말투", "t-structure": "", "t-rules": ""})
        self.assertEqual(SiteTemplate.objects.get(blog=self.memorily).tone, "새 말투")
        self.client.post(url, {"part": "format", "f-guide": "새 포맷"})
        self.assertEqual(PlatformFormat.objects.get(platform="tistory").guide, "새 포맷")
        self.assertContains(self.client.get(url), "자바 정리")

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
