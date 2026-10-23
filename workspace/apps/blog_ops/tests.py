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

    def _pc(self, results):
        import json
        return self.client.post(reverse("blog_ops:api_feeds"), json.dumps({"token": self.token, "results": results}),
                                content_type="application/json")

    def test_week_grid_counts_feed_and_marked_posts_once(self):
        """모니터링 (2026-10-22 사용자): 사이트 × 요일 한 주. RSS 글과 글 관리에서 발행 완료한 글은 제목이 같으면 한 번만"""
        from apps.writing.models import Post
        FeedEntry.objects.create(blog=self.nunip, title="오늘 글", url="https://ex.tistory.com/9", published_at=timezone.now())
        Post.objects.create(title="오늘 글", stage="post", target="눈잎", publish_status="done", published_on=self.today)
        Post.objects.create(title="RSS 에 없는 글", stage="post", target="눈잎", publish_status="done", published_on=self.today)
        Plan.objects.create(blog=self.nunip, planned_on=self.today, title="예전 계획 글", status="published", published_on=self.today)
        res = self.client.get(INDEX)
        self.assertEqual(res.status_code, 200)
        row = next(r for r in res.context["rows"] if r["blog"] == self.nunip)
        self.assertEqual(row["sum"], 3)
        day = dict(res.context["day_groups"])["눈잎"]  # 왼쪽 아래 '오늘 발행' (2026-10-23)
        self.assertEqual(sorted(x["title"] for x in day), ["RSS 에 없는 글", "예전 계획 글", "오늘 글"])
        self.assertContains(res, f'?date={self.today.isoformat()}&amp;site={self.nunip.pk}')  # 칸을 누르면 그날 그 사이트 글
        # 날짜를 고르면 그 주, ← → 는 한 주씩
        res = self.client.get(INDEX, {"date": "2026-10-15"})
        self.assertEqual(res.context["start"].isoformat(), "2026-10-12")
        self.assertEqual((res.context["prev"], res.context["next"]), ("2026-10-08", "2026-10-22"))
        self.assertEqual(len(res.context["strip"]), 7)

    def test_pc_report_marks_placement_published(self):
        """PC 가 읽은 RSS 를 보내면 저장하고, 제목(변환 제목)이 같은 그 사이트의 미발행 넣은 곳은 발행 완료로"""
        from apps.blog_types.models import Placement, SiteCategory
        from apps.writing.models import Post
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        self.token = "tok-123"
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, self.token)
        cat = SiteCategory.objects.create(blog=self.nunip, name="정보")
        post = Post.objects.create(title="원고 제목", stage="post", target="눈잎")
        pl = Placement.objects.create(site_category=cat, tistory_post=post, converted_title="독감  무료접종 일정")
        other = Post.objects.create(title="사이트만 정한 글", stage="post", target="눈잎")
        now = timezone.now()
        old = (now - timedelta(days=30)).isoformat()
        res = self._pc([{"blog": self.nunip.pk, "ok": True, "message": "", "items": [
            ["독감 무료접종 일정", "https://ex.tistory.com/1", now.isoformat()],
            ["사이트만 정한 글", "https://ex.tistory.com/2", old],  # 글을 만들기 전에 올라온 같은 제목 옛 글
        ]}])
        self.assertEqual(res.status_code, 200)
        self.assertIn("발행 완료 1건", res.json()["results"][0]["message"])
        pl.refresh_from_db(); post.refresh_from_db(); other.refresh_from_db()
        self.assertEqual((pl.status, post.publish_status, post.published_on), ("published", "done", timezone.localdate()))
        self.assertEqual(other.publish_status, "todo")
        self.assertEqual(FeedEntry.objects.filter(blog=self.nunip).count(), 2)
        self.assertTrue(FeedState.objects.get(blog=self.nunip).ok)
        res = self._pc([{"blog": self.nunip.pk, "ok": False, "message": "PC에서 접속하지 못했어요", "items": []}])
        self.assertEqual(FeedState.objects.get(blog=self.nunip).message, "PC에서 접속하지 못했어요")
        self.token = "wrong"
        self.assertEqual(self._pc([]).status_code, 403)

    def test_check_hands_feeds_to_pc(self):
        """'발행 확인': PC 에 넘길 안내 (보낼 주소 + 토큰 + RSS 주소). 토큰이 없으면 막는다"""
        import json
        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        self.assertEqual(self.client.post(reverse("blog_ops:check")).status_code, 400)
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        res = self.client.post(reverse("blog_ops:check")).json()
        head, _, body = res["prompt"].partition("\n")
        self.assertEqual(head, "# 발행 확인")
        payload = json.loads(body)
        self.assertTrue(payload["api"].endswith(reverse("blog_ops:api_feeds")))
        self.assertIn("https://ex.tistory.com/rss", [f["url"] for f in payload["feeds"]])
        self.assertTrue(res["key"].startswith("fd-"))


class SiteLinksTests(TestCase):
    """사이트 주소 (2026-10-22 사용자): 모니터링에 바로가기, 홈에 주소 정리 · 줄마다 복사 · 전체 복사."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))

    def test_monitoring_link_and_home_addresses(self):
        res = self.client.get(reverse("blog_ops:index"))
        self.assertContains(res, 'class="op-link" href="https://bambam2222.blogspot.com/"')
        home = self.client.get("/")
        self.assertContains(home, "사이트 주소")
        self.assertIn("밤밤 https://bambam2222.blogspot.com/", home.context["sites_text"])
        self.assertEqual(len(home.context["sites_text"].splitlines()), len(home.context["sites"]))
        self.assertContains(home, 'data-copy-text="https://nunip.tistory.com/"')


class DashboardTests(TestCase):
    """모니터링 네 칸 (2026-10-23 사용자): 발행 실적 · 일일루틴 글쓰기 / 그날 발행(변환·발행 완료) · 오늘의 글(발행예정으로)"""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        self.nunip = Blog.objects.get(name="눈잎")
        self.today = timezone.localdate()

    def test_four_panels(self):
        from apps.blog_types.models import Placement, SiteCategory
        from apps.writing.models import Post
        planned = Post.objects.create(title="오늘 예정", stage="post", target="눈잎", planned_on=self.today)
        Placement.objects.create(site_category=SiteCategory.objects.get(blog__name="눈잎", name="공모주"), tistory_post=planned)
        Post.objects.create(title="오늘 발행함", stage="post", target="눈잎", publish_status="done", published_on=self.today)
        Post.objects.create(title="내일 예정", stage="post", target="눈잎", planned_on=self.today + timedelta(days=1))
        temp = Post.objects.create(title="오늘 쓴 임시글", stage="temp", target="밤밤")
        res = self.client.get(INDEX)
        self.assertEqual(res.status_code, 200)
        groups = dict(res.context["day_groups"])
        self.assertEqual([(x["title"], x["state"]) for x in groups["눈잎"]], [("오늘 예정", "planned"), ("오늘 발행함", "done")])
        self.assertContains(res, 'data-st-run="')  # 변환
        self.assertContains(res, 'name="publish" value="done"')  # 발행 완료
        new = dict(res.context["new_groups"])
        self.assertIn("오늘 쓴 임시글", [p.title for p in new["밤밤"]])
        # 오늘의 글: 발행예정은 파랑, 발행 완료는 초록 (2026-10-23 사용자)
        self.assertContains(res, '<span class="badge blue od-state">발행예정</span>', html=False)
        self.assertContains(res, '<span class="badge green od-state">발행 완료</span>', html=False)
        self.assertContains(res, reverse("posts:promote"))
        self.assertEqual(res.context["wr"]["routine"].key, "writing")
        self.assertContains(res, "글쓰기 실행")
        for text in ["발행 실적", "일일루틴 글쓰기", "오늘 발행", "오늘의 글"]:
            self.assertContains(res, text)
        self.assertNotContains(res, "이번 주 발행")  # 숫자 칸 줄은 뺐다
        self.client.post(reverse("posts:promote"), {"ids": f"tistory:{temp.pk}", "next": INDEX})
        temp.refresh_from_db()
        self.assertEqual(temp.stage, "post")  # 임시글에서 바로 발행예정

    def test_cell_click_filters_day_panel(self):
        from apps.writing.models import Post
        day = self.today - timedelta(days=1)
        Post.objects.create(title="어제 발행", stage="post", target="눈잎", publish_status="done", published_on=day)
        Post.objects.create(title="어제 밤밤", stage="post", target="밤밤", publish_status="done", published_on=day)
        res = self.client.get(INDEX, {"date": day.isoformat(), "site": self.nunip.pk})
        self.assertEqual([n for n, _ in res.context["day_groups"]], ["눈잎"])
        self.assertContains(res, "오늘 · 모든 사이트")


    def test_rss_row_with_converted_title_is_not_doubled(self):
        """밤밤 코스피 (2026-10-23 사용자): 원문 제목과 블로그에 올라간 변환 제목이 달라도 한 줄"""
        from apps.blog_types.models import Placement, SiteCategory
        from apps.writing.models import Post
        bambam = Blog.objects.get(name="밤밤")
        post = Post.objects.create(title="코스피 -4.13%까지", stage="post", target="밤밤", publish_status="done",
                                   published_on=self.today)
        Placement.objects.create(site_category=SiteCategory.objects.get_or_create(blog=bambam, name="주식")[0], tistory_post=post,
                                 converted_title="코스피 -4.12%까지", status="published")
        FeedEntry.objects.create(blog=bambam, title="코스피 -4.12%까지", url="https://bambam2222.blogspot.com/1.html",
                                 published_at=timezone.now())
        res = self.client.get(INDEX)
        self.assertEqual([x["title"] for x in dict(res.context["day_groups"])["밤밤"]], ["코스피 -4.13%까지"])

class FeedTitleTests(TestCase):
    """티스토리 RSS 의 '&amp;middot;' (2026-10-23 사용자: 눈잎 어제 숫자가 안 맞았다)."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        self.nunip = Blog.objects.get(name="눈잎")

    def test_double_escaped_title_matches_post_and_date_moves_back(self):
        from datetime import datetime

        from apps.writing.models import Post
        yesterday = timezone.localdate() - timedelta(days=1)
        rss = ("<rss><channel><item><title>청약&amp;middot;환불 정리</title><link>https://nunip.tistory.com/9</link>"
               f"<pubDate>{yesterday:%a, %d %b %Y} 16:11:58 +0900</pubDate></item></channel></rss>")
        items = feeds.parse(rss.encode())
        self.assertEqual(items[0][0], "청약·환불 정리")
        post = Post.objects.create(title="청약·환불 정리", stage="post", target="눈잎", publish_status="done",
                                   published_on=timezone.localdate())  # 오늘 '발행 완료'를 눌렀다
        feeds.record(self.nunip, True, "", items)
        post.refresh_from_db()
        self.assertEqual(post.published_on, yesterday)  # RSS 에 올라온 날로
        res = self.client.get(INDEX, {"date": yesterday.isoformat()})
        row = next(r for r in res.context["rows"] if r["blog"] == self.nunip)
        self.assertEqual(sum(c["count"] for c in row["cells"]), 1)  # 두 번 세지 않는다


class DashboardRunTests(TestCase):
    """모니터링 (2026-10-23 사용자): 글쓰기 결과 줄마다 실행 · 오늘의 글에서 옮긴 글은 오늘 발행에."""

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))

    def test_promote_shows_in_today_and_rows_have_run(self):
        from apps.writing.models import Post
        post = Post.objects.create(title="오늘의 AI 글", stage="temp", target="memorily")
        self.client.post(reverse("posts:promote"), {"ids": f"tistory:{post.pk}", "next": INDEX})
        post.refresh_from_db()
        self.assertEqual((post.stage, post.planned_on), ("post", timezone.localdate()))
        undated = Post.objects.create(title="예정일 없는 오늘 글", stage="post", target="memorily")
        res = self.client.get(INDEX)
        titles = [x["title"] for _, items in res.context["day_groups"] for x in items]
        self.assertIn("오늘의 AI 글", titles)
        self.assertIn(undated.title, titles)
        self.assertContains(res, reverse("routines:topic_run"))  # 줄 실행 스크립트
