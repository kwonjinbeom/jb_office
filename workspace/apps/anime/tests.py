import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.menus import build_nav, find_menu, menu_keys_for

from .models import AnimeTitle


class AnimeTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("tester", password="pw-test-1234"))
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "00_작업순서.md").write_text("# 글 쓰는 순서\n\n공통", encoding="utf-8")
        (root / "02_블리치.md").write_text("# 블리치\n\n상태: 준비\n\n| a | b |\n|---|---|\n| 1 | 2 |", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_lists_guide_and_works(self):
        with override_settings(ANIME_DIR=self.tmp.name):
            res = self.client.get(reverse("anime:index"))
            self.assertContains(res, "글 쓰는 순서")
            self.assertContains(res, "준비")
            self.assertEqual(res.context["work_count"], 6)  # 이미 쓴 6작품이 담겨 있다 (migration 0002)
            res = self.client.get(reverse("anime:index"), {"d": "02_블리치"})
            self.assertContains(res, "<table>")  # md 표가 그려진다
            self.assertEqual(res.context["current"]["anime"].title, "블리치")  # md 와 애니가 이어진다

    def test_catalog_seeded_with_status(self):
        self.assertGreaterEqual(AnimeTitle.objects.count(), 30)
        self.assertEqual(AnimeTitle.objects.get(title="나루토").status, "published")
        self.assertEqual(set(AnimeTitle.objects.filter(picked=True).values_list("status", flat=True)), {"published", "written"})
        self.assertEqual(AnimeTitle.objects.get(title="진격의 거인").status, "todo")

    def test_pick_unpick_status_add_delete(self):
        with override_settings(ANIME_DIR=self.tmp.name):
            aot = AnimeTitle.objects.get(title="진격의 거인")
            self.client.post(reverse("anime:pick", args=[aot.pk]), {"picked": "1", "next": "https://evil.example/"})
            aot.refresh_from_db()
            self.assertTrue(aot.picked)
            res = self.client.get(reverse("anime:index"), {"a": aot.pk})
            self.assertEqual(res.context["current"]["anime"], aot)
            self.assertContains(res, "아직 작품 md 가 없습니다")
            self.client.post(reverse("anime:status", args=[aot.pk]), {"status": "doing"})
            self.client.post(reverse("anime:status", args=[aot.pk]), {"status": "nope"})  # 없는 상태는 무시
            aot.refresh_from_db()
            self.assertEqual(aot.status, "doing")
            res = self.client.post(reverse("anime:pick", args=[aot.pk]), {"picked": "0", "next": "https://evil.example/"})
            self.assertRedirects(res, reverse("anime:index"), fetch_redirect_response=False)  # 바깥 주소로는 안 간다
            aot.refresh_from_db()
            self.assertFalse(aot.picked)
            self.client.post(reverse("anime:add"), {"title": "  새 장편  "})
            self.client.post(reverse("anime:add"), {"title": "새 장편"})  # 같은 제목은 하나만
            self.assertEqual(AnimeTitle.objects.filter(title="새 장편").count(), 1)
            new = AnimeTitle.objects.get(title="새 장편")
            self.assertEqual(new.order, AnimeTitle.objects.exclude(pk=new.pk).order_by("-order")[0].order + 10)
            self.client.post(reverse("anime:delete", args=[new.pk]))
            self.assertFalse(AnimeTitle.objects.filter(pk=new.pk).exists())
            self.assertTrue(AnimeTitle.all_objects.filter(pk=new.pk).exists())  # 휴지통

    def test_menu_has_memorily_tistory_level(self):
        """블로그·카페 › memorily 티스토리 › 블로그 자동화 · 애니 총정리 (2026-10-21 사용자)"""
        self.assertEqual(find_menu("anime").title, "애니 총정리")
        self.assertEqual(find_menu("series").title, "블로그 자동화")
        self.assertEqual(menu_keys_for("anime", "index"), ["anime"])
        blog = next(n for n in build_nav("anime") if n["menu"].key == "blog")
        group = next(c for c in blog["children"] if c["menu"].key == "memorily_tistory")
        self.assertTrue(blog["open"] and group["active"])
        self.assertEqual([g["menu"].key for g in group["children"]], ["series", "anime", "anime_seasons"])
        res = self.client.get(reverse("series:index"))
        self.assertContains(res, 'class="nav-sub-label active"')
