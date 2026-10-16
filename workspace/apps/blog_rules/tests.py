from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.blog_ops.models import Plan
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
        self.assertEqual((res.context["mode"], res.context["target_total"]), ("day", 3))  # 운영 중인 셋 × 1편
        self.assertEqual(res.context["accounts"], [("카카오 계정 1", 2)])
        for text in ["jinbaam.tistory.com", "nunip.tistory.com", "쇼핑커넥트 링크는", "하루 편수 정하기", "하루 1편 · 애드센스",
                     "발행", "임시저장", "일별", "월별", "data-open-picker"]:
            self.assertContains(res, text)
        self.assertNotContains(res, "기출문제")  # 일반 규칙은 화면에 없다

    def test_published_and_drafts_by_day_and_month(self):
        nunip, naver = Blog.objects.get(name="눈잎"), Blog.objects.get(name="black_lukey")
        day = date(2026, 10, 14)
        Plan.objects.create(blog=nunip, title="발행한 글", planned_on=day, status="published", published_on=day)
        Plan.objects.create(blog=nunip, title="손질 중", planned_on=day, status="edit")
        Plan.objects.create(blog=naver, title="다음 날 원고", planned_on=day + timedelta(days=1))
        res = self.client.get(INDEX, {"date": "2026-10-14"})
        rows = {b.name: (b.published, b.target, b.drafts) for b in res.context["blogs"]}
        self.assertEqual(rows["눈잎"], (1, 1, 1))
        self.assertEqual(rows["black_lukey"], (0, 1, 0))
        self.assertEqual([d["count"] for d in res.context["strip"]], [0, 0, 1, 0, 0, 0, 0])  # 월~일, 14일은 수요일
        res = self.client.get(INDEX, {"month": "2026-10"})
        rows = {b.name: (b.published, b.target, b.drafts) for b in res.context["blogs"]}
        self.assertEqual(res.context["mode"], "month")
        self.assertEqual(rows["눈잎"], (1, 31, 1))
        self.assertEqual(rows["black_lukey"], (0, 31, 1))
        self.assertEqual(rows["밤밤"][1], 0)  # 준비 중인 사이트는 목표 없음
        self.assertEqual(len(res.context["strip"]), 12)
        self.assertEqual(res.context["nav"]["prev"], "?month=2026-09")

    def test_quick_add_edit_delete_check(self):
        blog = Blog.objects.get(name="밤밤")
        res = self.client.post(reverse("blog_rules:rule_add"), {"blog": blog.pk, "body": "  사진은   직접 찍은 것만 ", "keep": "month=2026-10"})
        self.assertEqual(res["Location"], f"{INDEX}?month=2026-10#site-{blog.pk}")  # 보던 달 그대로
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
        self.assertEqual(res.context["target_total"], 3)  # 준비 상태는 목표에 넣지 않는다
