import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.menus import build_nav, find_menu, menu_keys_for


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
            self.assertEqual(res.context["works"], 1)
            res = self.client.get(reverse("anime:index"), {"d": "02_블리치"})
            self.assertContains(res, "<table>")  # md 표가 그려진다

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
