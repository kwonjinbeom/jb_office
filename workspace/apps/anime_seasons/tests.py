import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.menus import build_nav, find_menu

from .models import SeasonAnime

INDEX = reverse("anime_seasons:index")


class AnimeSeasonTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))

    def test_seeded_2026_quarters(self):
        """migration 0002 가 2026년 1~3분기 방영작을 넣는다 (방영 시작일 기준 분기)."""
        for q in (1, 2, 3):
            self.assertGreater(SeasonAnime.objects.filter(year=2026, quarter=q).count(), 40)
        self.assertFalse(SeasonAnime.objects.filter(year=2026, quarter=4).exists())
        frieren = SeasonAnime.objects.get(title="장송의 프리렌 2기")
        self.assertEqual((frieren.quarter, frieren.aired), (1, datetime.date(2026, 1, 16)))

    def test_index_lists_and_move(self):
        res = self.client.get(INDEX, {"y": 2026, "q": 1})
        self.assertContains(res, "장송의 프리렌 2기")
        frieren = SeasonAnime.objects.get(title="장송의 프리렌 2기")
        self.assertIn(frieren, res.context["todo"])
        res = self.client.post(reverse("anime_seasons:move", args=[frieren.pk]), {"watched": "1"})
        self.assertEqual(res.json(), {"ok": True, "watched": True})
        res = self.client.get(INDEX, {"y": 2026, "q": 1})
        self.assertIn(frieren, res.context["done"])
        self.assertNotIn(frieren, res.context["todo"])
        self.assertEqual(next(s for s in res.context["quarters"] if s["q"] == 1)["seen"], 1)
        self.client.post(reverse("anime_seasons:move", args=[frieren.pk]), {"watched": "0"})
        frieren.refresh_from_db()
        self.assertFalse(frieren.watched)
        self.assertIsNone(frieren.watched_at)

    def test_save_review_moves_to_watched(self):
        a = SeasonAnime.objects.get(title="장송의 프리렌 2기")
        res = self.client.post(reverse("anime_seasons:save", args=[a.pk]),
                               {"rating": "9", "pick": "on", "one_line": "잔잔한데 강하다", "review": "길게"})
        self.assertRedirects(res, f"{INDEX}?y=2026&q=1&a={a.pk}")
        a.refresh_from_db()
        self.assertEqual((a.rating, a.stars, a.pick, a.watched), (9, 4.5, True, True))
        res = self.client.get(INDEX, {"y": 2026, "q": 1, "a": a.pk})
        self.assertEqual(res.context["picked"], a)
        self.assertContains(res, "★ 4.5")
        self.client.post(reverse("anime_seasons:save", args=[a.pk]), {"rating": "99"})  # 범위 밖은 비운다
        a.refresh_from_db()
        self.assertIsNone(a.rating)

    def test_add_uses_aired_quarter_and_delete_to_trash(self):
        self.client.post(reverse("anime_seasons:add"), {"title": "새 작품", "aired": "2026-11-02", "year": 2026, "quarter": 1})
        a = SeasonAnime.objects.get(title="새 작품")
        self.assertEqual((a.year, a.quarter), (2026, 4))
        self.client.post(reverse("anime_seasons:add"), {"title": "날짜 없음", "year": 2026, "quarter": 2})
        self.assertEqual(SeasonAnime.objects.get(title="날짜 없음").quarter, 2)
        self.client.post(reverse("anime_seasons:delete", args=[a.pk]))
        self.assertFalse(SeasonAnime.objects.filter(pk=a.pk).exists())
        self.assertTrue(SeasonAnime.all_objects.filter(pk=a.pk).exists())  # 휴지통

    def test_menu_under_memorily_tistory(self):
        self.assertEqual(find_menu("anime_seasons").title, "분기별 애니 추천 및 후기")
        blog = next(n for n in build_nav("anime_seasons") if n["menu"].key == "blog")
        group = next(c for c in blog["children"] if c["menu"].key == "memorily_tistory")
        self.assertEqual([g["menu"].key for g in group["children"]], ["series", "anime", "anime_seasons"])
        self.assertTrue(group["active"])
