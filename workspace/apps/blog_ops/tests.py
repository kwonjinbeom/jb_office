import urllib.error
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.blog_rules.models import Blog

from . import feeds
from .models import FeedEntry, FeedState, Plan

INDEX = reverse("blog_ops:index")

RSS = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>t</title>
<item><title>독감 무료접종 일정</title><link>https://ex.tistory.com/1</link><pubDate>{d1}</pubDate></item>
<item><title>오래된 글</title><link>https://ex.tistory.com/0</link><pubDate>Mon, 05 Jan 2026 09:00:00 +0900</pubDate></item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>블로거 글</title><link rel="alternate" href="https://bambam2222.blogspot.com/a.html"/>
<published>2026-10-16T10:00:00+09:00</published></entry></feed>"""


class BlogOpsTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("tester", password="pw-test-1234")
        self.client.force_login(user)
        self.nunip = Blog.objects.get(name="눈잎")
        self.nunip.address = "https://ex.tistory.com"
        self.nunip.save()
        self.today = timezone.localdate()

    def test_feed_url_rules(self):
        self.assertEqual(feeds.feed_url(self.nunip), "https://ex.tistory.com/rss")
        self.assertEqual(feeds.feed_url(Blog.objects.get(name="black_lukey")), "https://rss.blog.naver.com/black_lukey.xml")
        self.assertEqual(feeds.feed_url(Blog.objects.get(platform="blogger")),
                         "https://bambam2222.blogspot.com/feeds/posts/default?alt=rss")
        self.assertEqual(feeds.feed_url(Blog.objects.get(name="memorily")), "https://jinbaam.tistory.com/rss")

    def test_parse_rss_and_atom(self):
        now = timezone.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
        items = feeds.parse(RSS.format(d1=now).encode())
        self.assertEqual([t for t, _, _ in items], ["독감 무료접종 일정", "오래된 글"])
        atom = feeds.parse(ATOM.encode())
        self.assertEqual(atom[0][:2], ("블로거 글", "https://bambam2222.blogspot.com/a.html"))

    def test_sync_marks_matching_plan_published(self):
        plan = Plan.objects.create(blog=self.nunip, planned_on=self.today, title="독감  무료접종 일정", status="scheduled")
        now = timezone.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
        state = feeds.sync(self.nunip, fetch=lambda url: RSS.format(d1=now).encode())
        self.assertTrue(state.ok)
        self.assertEqual(FeedEntry.objects.filter(blog=self.nunip).count(), 2)
        plan.refresh_from_db()
        self.assertEqual((plan.status, plan.url), ("published", "https://ex.tistory.com/1"))
        # 두 번 읽어도 같은 글은 한 번만
        feeds.sync(self.nunip, fetch=lambda url: RSS.format(d1=now).encode())
        self.assertEqual(FeedEntry.objects.filter(blog=self.nunip).count(), 2)

    def test_sync_blocked_server_reports_reason(self):
        def blocked(url):
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        state = feeds.sync(self.nunip, fetch=blocked)
        self.assertFalse(state.ok)
        self.assertIn("허용 목록", state.message)
        no_addr = Blog.objects.get(platform="wordpress")
        state = feeds.sync(no_addr)
        self.assertIn("주소가 없어", state.message)

    def test_week_counts_plan_and_feed_once(self):
        Plan.objects.create(blog=self.nunip, planned_on=self.today, title="오늘 글", status="published",
                            published_on=self.today, url="https://ex.tistory.com/9")
        FeedEntry.objects.create(blog=self.nunip, title="오늘 글", url="https://ex.tistory.com/9",
                                 published_at=timezone.now())
        Plan.objects.create(blog=self.nunip, planned_on=self.today, title="주소 없이 발행", status="published",
                            published_on=self.today)
        FeedEntry.objects.create(blog=self.nunip, title="주소 없이 발행", url="https://ex.tistory.com/10",
                                 published_at=timezone.now())
        res = self.client.get(INDEX)
        self.assertEqual(res.status_code, 200)
        row = next(r for r in res.context["rows"] if r["blog"] == self.nunip)
        self.assertEqual(row["sum"], 2)  # 계획 기록과 RSS 기록이 같은 글이면 한 번만
        self.assertEqual(dict(res.context["tiles"])["오늘 발행"], "2/3")
        self.assertContains(res, "운영")

    def test_plan_add_status_edit_delete(self):
        self.client.post(reverse("blog_ops:plan_add"), {"planned_on": self.today.isoformat(), "blog": self.nunip.pk,
                                                         "title": "  새   계획 "})
        plan = Plan.objects.get(title="새 계획")
        self.client.post(reverse("blog_ops:plan_status", args=[plan.pk]), {"status": "published"})
        plan.refresh_from_db()
        self.assertEqual((plan.status, plan.published_on), ("published", self.today))
        self.client.post(reverse("blog_ops:plan_edit", args=[plan.pk]), {
            "planned_on": self.today.isoformat(), "blog": self.nunip.pk, "title": "새 계획", "status": "published",
            "url": "https://ex.tistory.com/77", "published_on": self.today.isoformat(), "memo": "",
        })
        plan.refresh_from_db()
        self.assertEqual(plan.url, "https://ex.tistory.com/77")
        self.client.post(reverse("blog_ops:plan_delete", args=[plan.pk]))
        self.assertFalse(Plan.objects.filter(pk=plan.pk).exists())

    def test_late_unpublished_plans_stay_visible(self):
        old = Plan.objects.create(blog=self.nunip, planned_on=self.today - timedelta(days=14), title="밀린 글")
        res = self.client.get(INDEX)
        self.assertIn(old, list(res.context["plans"]))
        self.assertTrue(FeedState.objects.count() == 0)
