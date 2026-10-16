from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import TrashEntry

from .models import Blog, Rule

INDEX = reverse("blog_rules:index")


class BlogRulesTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)

    def test_seed(self):
        self.assertEqual(list(Blog.objects.values_list("name", flat=True)),
                         ["memorily", "눈잎", "black_lukey", "밤밤", "워드프레스"])
        self.assertTrue(Blog.objects.get(name="밤밤").content.startswith("정보성"))
        self.assertTrue(Blog.objects.get(name="memorily").content.startswith("IT·개발"))
        naver = Blog.objects.get(name="black_lukey")
        self.assertEqual((naver.platform, naver.daily, naver.address, naver.daily_note),
                         ("naver", 1, "https://blog.naver.com/black_lukey", ""))
        blogger = Blog.objects.get(platform="blogger")
        self.assertEqual((blogger.address, blogger.status), ("https://bambam2222.blogspot.com/", "ready"))

    def test_checks_by_site_and_generic_rules_in_trash(self):
        # 0007: 체크는 모두 사이트에 붙고, 예전 일반 규칙은 휴지통 (7일 복원)
        self.assertFalse(Rule.objects.filter(blog__isnull=True).exists())
        for name in ["memorily", "눈잎", "black_lukey", "밤밤", "워드프레스"]:
            self.assertTrue(Rule.objects.filter(blog__name=name).exists(), name)
        self.assertTrue(Rule.objects.filter(blog__name="눈잎", body__contains="밤밤과 주제").exists())
        old = Rule.all_objects.filter(blog__isnull=True)
        self.assertTrue(old.exists())
        self.assertFalse(old.filter(deleted_at__isnull=True).exists())
        self.assertEqual(TrashEntry.objects.filter(model_label="blog_rules.rule").count(), old.count())

    def test_page_shows_sites_and_checks(self):
        res = self.client.get(INDEX)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["daily_total"], 3)  # 운영 중인 셋 × 1편
        self.assertEqual(res.context["accounts"], [("카카오 계정 1", 2)])
        for text in ["jinbaam.tistory.com", "nunip.tistory.com", "쇼핑커넥트 링크는", "하루 편수 정하기", "보류"]:
            self.assertContains(res, text)
        self.assertNotContains(res, "기출문제")  # 일반 규칙은 화면에 없다

    def test_quick_add_edit_delete_check(self):
        blog = Blog.objects.get(name="밤밤")
        self.client.post(reverse("blog_rules:rule_add"), {"blog": blog.pk, "body": "  사진은   직접 찍은 것만 "})
        rule = Rule.objects.get(body="사진은 직접 찍은 것만")
        self.assertEqual((rule.blog, rule.order), (blog, blog.checks.count()))
        self.client.post(reverse("blog_rules:rule_add"), {"blog": 9999, "body": "x"})
        self.assertFalse(Rule.objects.filter(body="x").exists())
        self.client.post(reverse("blog_rules:rule_edit", args=[rule.pk]), {"blog": blog.pk, "body": "사진은 직접", "note": ""})
        rule.refresh_from_db()
        self.assertEqual(rule.body, "사진은 직접")
        self.client.post(reverse("blog_rules:delete", args=["rule", rule.pk]))
        self.assertNotContains(self.client.get(INDEX), "사진은 직접")
        self.assertTrue(Rule.all_objects.filter(pk=rule.pk, deleted_at__isnull=False).exists())

    def test_add_edit_blog(self):
        self.client.post(reverse("blog_rules:blog_create"), {
            "name": "세번째", "platform": "tistory", "status": "ready", "address": "", "account": "카카오 계정 1",
            "revenue": "", "daily": 1, "daily_note": "", "content": "", "kpi": "", "note": "",
        })
        b = Blog.objects.get(name="세번째")
        self.assertEqual(b.order, 6)
        res = self.client.get(INDEX)
        self.assertEqual(res.context["daily_total"], 3)  # 준비 상태는 오늘 목표에 넣지 않는다
