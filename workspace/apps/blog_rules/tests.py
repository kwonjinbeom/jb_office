from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Blog, Rule

INDEX = reverse("blog_rules:index")


class BlogRulesTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)

    def test_seed(self):
        self.assertEqual(list(Blog.objects.values_list("name", flat=True)),
                         ["memorily", "눈잎", "black_lukey", "밤밤", "워드프레스"])
        # 0004: 블로거 = 밤밤(정보성), 품질 순서와 겹침 금지 규칙
        self.assertTrue(Blog.objects.get(name="밤밤").content.startswith("정보성"))
        self.assertTrue(Rule.objects.filter(group="common", body__startswith="블로그끼리 내용이 겹치는").exists())
        self.assertTrue(Rule.objects.filter(group="common", body__contains="눈잎(티스토리) > 밤밤(블로거)").exists())
        naver = Blog.objects.get(name="black_lukey")
        self.assertEqual((naver.platform, naver.daily, naver.address), ("naver", 1, "https://blog.naver.com/black_lukey"))
        self.assertEqual(Rule.objects.filter(group="check").count(), 5)
        self.assertTrue(Rule.objects.filter(group="ban", body__contains="기출문제").exists())
        # 0003: memorily 는 IT 기반, 블로거는 주소가 생겨 '준비'
        self.assertTrue(Blog.objects.get(name="memorily").content.startswith("IT 기반"))
        blogger = Blog.objects.get(platform="blogger")
        self.assertEqual((blogger.address, blogger.status), ("https://bambam2222.blogspot.com/", "ready"))

    def test_page_shows_cards_totals_and_groups(self):
        res = self.client.get(INDEX)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["daily_total"], 3)  # 운영 중인 셋 × 1편, 보류는 빼고
        self.assertEqual([(n, t) for n, t, _ in res.context["accounts"]], [("카카오 계정 1", 2)])
        for text in ["memorily", "눈잎", "black_lukey", "애드센스 승인 뒤 2편", "발행 전 손질", "금지", "보류"]:
            self.assertContains(res, text)
        self.assertContains(res, "규칙")  # 블로그·카페 아래 중메뉴

    def test_quick_add_and_edit_rule(self):
        self.client.post(reverse("blog_rules:rule_add"), {"group": "naver", "body": "  사진은   직접 찍은 것만 "})
        rule = Rule.objects.get(body="사진은 직접 찍은 것만")
        self.assertEqual(rule.order, Rule.objects.filter(group="naver").count())
        self.client.post(reverse("blog_rules:rule_add"), {"group": "없는묶음", "body": "x"})
        self.assertFalse(Rule.objects.filter(body="x").exists())
        self.client.post(reverse("blog_rules:rule_edit", args=[rule.pk]), {"group": "common", "body": "사진은 직접", "note": ""})
        rule.refresh_from_db()
        self.assertEqual((rule.group, rule.body), ("common", "사진은 직접"))

    def test_add_edit_blog(self):
        self.client.post(reverse("blog_rules:blog_create"), {
            "name": "세번째", "platform": "tistory", "status": "ready", "address": "", "account": "카카오 계정 1",
            "revenue": "", "daily": 1, "daily_note": "", "content": "", "kpi": "", "note": "",
        })
        b = Blog.objects.get(name="세번째")
        self.assertEqual(b.order, 6)
        res = self.client.get(INDEX)
        self.assertEqual(res.context["daily_total"], 3)  # 준비 상태는 오늘 목표에 넣지 않는다

    def test_delete_goes_to_trash(self):
        rule = Rule.objects.first()
        self.client.post(reverse("blog_rules:delete", args=["rule", rule.pk]))
        self.assertFalse(Rule.objects.filter(pk=rule.pk).exists())
        self.assertTrue(Rule.all_objects.filter(pk=rule.pk, deleted_at__isnull=False).exists())
