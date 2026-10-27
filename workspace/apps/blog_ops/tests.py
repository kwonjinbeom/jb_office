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
        Blog.objects.filter(platform="wordpress").update(address="")  # 워드프레스는 0030 에서 주소가 생겼다
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


class SiteStatsTests(TestCase):
    """통계현황 (2026-10-23 사용자): 사이트별 방문자 · 공감 · 댓글 추이"""

    def setUp(self):
        user = get_user_model().objects.create_user("tester2", password="pw-test-1234")
        self.client.force_login(user)
        self.naver = Blog.objects.get(name="black_lukey")
        self.tistory = Blog.objects.get(name="memorily")
        self.today = timezone.localdate()

    def test_collect_naver_and_tistory(self):
        import json as _json
        from datetime import date as _date

        from . import stats
        day = _date(2026, 10, 23)
        # 네이버 (2026-10-24): 방문자 그래프는 빈 응답이라 모바일 블로그 정보의 오늘 방문자 · 누적
        info = _json.dumps({"result": {"dayVisitorCount": 12, "totalVisitorCount": 321}}).encode()
        posts = _json.dumps({"result": {"items": [{"sympathyCnt": 3, "commentCnt": 1}, {"sympathyCnt": "2", "commentCnt": 0}]}}).encode()
        pages = {stats.NAVER_INFO.format(id="black_lukey"): info, stats.NAVER_POSTS.format(id="black_lukey"): posts}
        got = stats.collect(stats.target(self.naver), fetch=lambda url: pages[url], today=day)
        self.assertEqual((got["visitors"], got["visitors_total"]), ({"2026-10-23": 12}, 321))
        self.assertEqual((got["likes_total"], got["comments_total"]), (5, 1))
        self.assertTrue(got["ok"])
        # 티스토리: 방문자는 스킨 조각, 공감·댓글은 RSS 의 최근 글마다 GET
        addr = self.tistory.address.rstrip("/")
        rss = (b"<rss><item><comments>https://x.tistory.com/entry/a#entry11comment</comments></item>"
               b"<item><comments>https://x.tistory.com/entry/b#entry10comment</comments></item></rss>")
        tpages = {
            addr + "/": b'<html><div id="jb-stat" hidden data-today="1,204" data-yesterday="987" data-total="5"></div></html>',
            addr + "/rss": rss,
            stats.TISTORY_LIKES.format(addr=addr, id="11"): b'{"data":{"reactionCounter":{"sum":2,"like":2}}}',
            stats.TISTORY_LIKES.format(addr=addr, id="10"): b'{"data":{"reactionCounter":{"sum":1}}}',
            stats.TISTORY_COMMENTS.format(addr=addr, id="11"): b'{"data":{"items":[],"totalItems":3}}',
            stats.TISTORY_COMMENTS.format(addr=addr, id="10"): b'{"data":{"items":[],"totalItems":0}}',
        }
        got = stats.collect(stats.target(self.tistory), fetch=lambda url: tpages[url], today=day)
        self.assertEqual(got["visitors"], {"2026-10-23": 1204, "2026-10-22": 987})
        self.assertEqual((got["visitors_total"], got["likes_total"], got["comments_total"]), (5, 3, 3))
        # 조각이 없으면 스킨 사이드바의 'Today : n · Yesterday : n'
        tpages[addr + "/"] = (b'<div class="box-visit"><h3>Total</h3><p class="text-total">31</p>'
                              b'<ul><li class="item-visit">Today : 1</li><li class="item-visit">Yesterday : 3</li></ul></div>')
        got = stats.collect(stats.target(self.tistory), fetch=lambda url: tpages[url], today=day)
        self.assertEqual((got["visitors"], got["visitors_total"]), ({"2026-10-23": 1, "2026-10-22": 3}, 31))
        tpages[addr + "/"] = b"<html></html>"
        got = stats.collect(stats.target(self.tistory), fetch=lambda url: tpages[url], today=day)
        self.assertTrue(got["ok"])  # 방문자 칸이 없어도 공감·댓글은 읽는다
        self.assertIn("스킨에 방문자 칸 없음", got["message"])
        got = stats.collect(stats.target(self.tistory), fetch=lambda url: b"<html></html>")
        self.assertFalse(got["ok"])
        self.assertIn("스킨에 방문자 칸이 없어요", got["message"])

    def test_collect_blogger_comments(self):
        import json as _json

        from . import stats
        blogger = Blog.objects.filter(platform="blogger").exclude(address="").first()
        feed = _json.dumps({"feed": {"entry": [{"thr$total": {"$t": "2"}}, {"thr$total": {"$t": "1"}}, {}]}}).encode()
        got = stats.collect(stats.target(blogger), fetch=lambda url: feed)
        self.assertEqual((got["visitors"], got["likes_total"], got["comments_total"]), ({}, 0, 3))
        self.assertTrue(got["ok"])
        self.assertIn("방문자는 GA4", got["message"])

    def test_naver_yesterday_filled_from_total(self):
        """네이버는 오늘 방문자만 준다: 다음 날 누적으로 어제를 마저 채운다 (어제 마지막 수집 뒤에 온 사람까지)"""
        from . import stats
        from .models import SiteStat
        y = self.today - timedelta(days=1)
        stats.record(self.naver, {"ok": True, "visitors": {y.isoformat(): 5}, "visitors_total": 105}, today=y)  # 어제 낮: 5명, 누적 105
        stats.record(self.naver, {"ok": True, "visitors": {self.today.isoformat(): 2}, "visitors_total": 111})  # 오늘: 2명, 누적 111
        self.assertEqual(SiteStat.objects.get(blog=self.naver, day=y).visitors, 9)  # 어제 시작 100 → 오늘 시작 109
        self.assertEqual(SiteStat.objects.get(blog=self.naver, day=self.today).visitors, 2)

    def test_record_keeps_hand_and_counts_daily_likes(self):
        from . import stats
        from .models import FeedState, SiteStat
        y = self.today - timedelta(days=1)
        SiteStat.objects.create(blog=self.naver, day=y, likes_total=10, comments_total=4)
        SiteStat.objects.create(blog=self.naver, day=y - timedelta(days=1), visitors=7, hand=True)
        stats.record(self.naver, {"ok": True, "message": "방문자 2일치 · 공감·댓글",
                                  "visitors": {y.isoformat(): 40, (y - timedelta(days=1)).isoformat(): 99},
                                  "likes_total": 13, "comments_total": 4})
        row = SiteStat.objects.get(blog=self.naver, day=self.today)
        self.assertEqual((row.likes, row.comments), (3, 0))  # 오늘 합계 − 어제 합계
        self.assertEqual(SiteStat.objects.get(blog=self.naver, day=y).visitors, 40)
        self.assertEqual(SiteStat.objects.get(blog=self.naver, day=y - timedelta(days=1)).visitors, 7)  # 직접 넣은 날은 그대로
        self.assertTrue(FeedState.objects.get(blog=self.naver).stat_ok)

    def test_page_tiles_top_pages_channels(self):
        """2026-10-27 사용자: 보기 쉽게 — 사이트 칸(기간 방문자 · 어제·오늘) · 하루 방문자 · 많이 본 글 · 어디서 왔나"""
        from . import stats
        from .models import SiteStat
        res = self.client.get(reverse("blog_ops:stats"))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.context["has_data"])
        self.assertContains(res, "지금 수집")
        y = self.today - timedelta(days=1)
        SiteStat.objects.create(blog=self.naver, day=y, visitors=10)
        SiteStat.objects.create(blog=self.naver, day=self.today, visitors=4)
        stats.record_ga4(self.tistory, {"daily": [[y.isoformat(), 30, 12]],
                                        "pages": [["/", "홈", 50, 20], ["/category/애니", "애니", 30, 9], ["/7", "교토 단풍", 21, 9]],
                                        "channels": [["Organic Search", 30], ["Direct", 10]]})
        res = self.client.get(reverse("blog_ops:stats"))  # 기본 7일 (2026-10-27 사용자)
        self.assertEqual(res.context["n"], 7)
        self.assertTrue(res.context["has_data"])
        tile = next(t for t in res.context["tiles"] if t["blog"] == self.naver)
        self.assertEqual((tile["visitors"], tile["yesterday"], tile["today"], tile["source"]), (14, 10, 4, "공개 숫자"))
        tile = next(t for t in res.context["tiles"] if t["blog"] == self.tistory)
        self.assertEqual((tile["visitors"], tile["views"], tile["source"]), (12, 30, "GA4"))
        self.assertEqual(res.context["total"]["visitors"], 26)
        self.assertEqual(len(res.context["chart"]["cols"]), 7)
        self.assertContains(res, "black_lukey~")  # 막대 말풍선 자료
        col = next(c for c in res.context["chart"]["cols"] if c["day"] == y)
        self.assertEqual((col["total"], len(col["segs"])), (22, 2))  # 그날 막대에 두 사이트를 쌓는다
        self.assertEqual([p["title"] for p in res.context["top"]], ["교토 단풍"])  # 첫 화면·카테고리는 뺀다
        self.assertEqual(res.context["top"][0]["url"], self.tistory.address.rstrip("/") + "/7")
        self.assertEqual([(c["name"], c["pct"]) for c in res.context["channels"]], [("검색", 75), ("직접", 25)])
        # 색은 사이트 순서로 고정: 운영 중이 아닌 사이트를 빼도 같은 색
        colors = {t["blog"].pk: t["color"] for t in res.context["tiles"]}
        self.assertEqual(len(set(colors.values())), len(colors))
        # 사이트 칸을 누르면 그 사이트만 (막대 · 많이 본 글 · 어디서 왔나)
        res = self.client.get(reverse("blog_ops:stats"), {"site": self.naver.pk})
        self.assertEqual(res.context["selected"], self.naver)
        self.assertEqual(next(c for c in res.context["chart"]["cols"] if c["day"] == y)["total"], 10)
        self.assertEqual((res.context["top"], res.context["channels"]), ([], []))
        self.assertContains(res, "네이버는 GA4 를 붙일 수 없어")

    def test_ga4_days_win_over_public_numbers(self):
        """GA4 가 채운 날은 공개 숫자(스킨 방문자 칸)가 방문자를 덮지 않는다. 글 목록은 수집마다 통째로 바뀐다."""
        import json as _json

        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        from . import stats
        from .models import SitePage, SiteStat
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        host = self.tistory.address.split("://")[-1].strip("/")
        body = {"token": "tok", "results": [], "stats": [], "ga4": [
            {"host": host, "daily": [[self.today.isoformat(), 50, 20]], "pages": [["/1", "a", 5, 3], ["/2", "b", 4, 2]], "channels": []}]}
        res = self.client.post(reverse("blog_ops:api_feeds"), _json.dumps(body), content_type="application/json")
        self.assertIn({"blog": "memorily GA4", "ok": True, "message": "GA4 1일 · 글 2"}, res.json()["results"])
        stats.record(self.tistory, {"ok": True, "visitors": {self.today.isoformat(): 999}})
        row = SiteStat.objects.get(blog=self.tistory, day=self.today)
        self.assertEqual((row.visitors, row.views), (20, 50))
        stats.record_ga4(self.tistory, {"daily": [], "pages": [["/3", "c", 1, 1]]})
        self.assertEqual(list(SitePage.objects.filter(blog=self.tistory).values_list("path", flat=True)), ["/3"])

    def test_pc_report_carries_stats_and_menu_order(self):
        import json as _json

        from apps.core.models import ROUTINE_BRIEF_TOKEN_KEY, AppSetting
        from .models import SiteStat
        AppSetting.set(ROUTINE_BRIEF_TOKEN_KEY, "tok")
        payload = _json.loads(self.client.post(reverse("blog_ops:check")).json()["prompt"].partition("\n")[2])
        self.assertIn({"blog": self.naver.pk, "name": "black_lukey", "platform": "naver",
                       "address": self.naver.address.rstrip("/"), "naver": "black_lukey"}, payload["stats"])
        res = self.client.post(reverse("blog_ops:api_feeds"), _json.dumps({"token": "tok", "results": [], "stats": [
            {"blog": self.naver.pk, "ok": True, "message": "방문자 1일치", "visitors": {self.today.isoformat(): 5}}]}),
            content_type="application/json")
        self.assertEqual(res.json()["results"][0]["blog"], "black_lukey 통계")
        self.assertEqual(SiteStat.objects.get(blog=self.naver, day=self.today).visitors, 5)
        nav = [c.title for m in self.client.get(reverse("blog_ops:stats")).context["MENUS"] if m.key == "blog" for c in m.children]
        self.assertEqual(nav[:2], ["통계현황", "모니터링"])


class WordpressStatsTests(TestCase):
    """워드프레스 통계 (2026-10-26): 댓글 수는 공개 REST, 공감은 없다, 방문자는 GA4 (2026-10-27)."""

    def test_collect_wordpress_comments(self):
        import json as _json

        from . import stats
        wp = Blog.objects.get(platform="wordpress")
        got = stats.collect(stats.target(wp), fetch=lambda url: _json.dumps([{"id": 1}, {"id": 2}]).encode())
        self.assertEqual((got["likes_total"], got["comments_total"]), (0, 2))
        self.assertIn("방문자는 GA4", got["message"])
